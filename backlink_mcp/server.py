"""
Backlink Builder MCP
--------------------
Scans a live site and/or its source code, then helps build *legitimate* backlinks:
citations & directories, guest-post / resource-page prospecting, outreach drafts,
link verification, internal-link fixes, and a local progress tracker.

It never auto-posts links anywhere (no comment/forum spam, PBNs or link buying) –
those violate Google's spam policies and get sites penalised.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.robotparser
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

import logging

import httpx
from bs4 import BeautifulSoup

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .countries import COUNTRIES, country_name, format_phone, region_matches, resolve_country
from .data import CATEGORY_HINTS, DIRECTORIES, FOOTPRINTS, NICHE_TAGS, OUTREACH_TEMPLATES

mcp = _Server(
    "backlink-builder",
    instructions=(
        "Workflow: scan_site and/or scan_codebase -> seo_link_audit (follow priority_fixes) -> generate_schema -> "
        "find_opportunities -> build_submission_kit -> qualify_prospect -> tracker_add -> draft_outreach -> "
        "verify_backlink. Never pass placeholder values (XXXX, 20XX, 'your address'); ask the user instead. "
        "Only put real, verifiable facts in outreach proof; never claim a past relationship. "
        "Use your own web search with the footprint queries from find_opportunities to find real "
        "prospects. Never post links automatically; the human submits/sends."
    ),
)

logging.getLogger("httpx").setLevel(logging.WARNING)
UA = "BacklinkBuilderMCP/1.0 (+site audit)"
DATA_DIR = Path(os.environ.get("BACKLINK_MCP_DATA", Path.home() / ".backlink-mcp"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
TRACKER = DATA_DIR / "tracker.json"
PROJECTS = DATA_DIR / "projects.json"
CUSTOM = DATA_DIR / "custom.json"
CACHE = DATA_DIR / "scans"
CACHE.mkdir(exist_ok=True)

STOP = set(
    """a an the and or but of to in on for with at by from as is are was were be been it its this that
    these those you your we our us they their i me my he she his her them not no yes do does did can will
    just more most very all any some about into over than then so such only also how what when where who
    why which here there home page click read contact us get best new one two using use via per etc
    """.split()
)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,6}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "venv", ".venv", "env",
             "__pycache__", ".cache", "coverage", ".turbo", "vendor", "staticfiles", ".svelte-kit"}
CODE_EXT = {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".astro", ".py",
            ".md", ".mdx", ".json", ".txt", ".xml", ".php"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "poetry.lock",
              "composer.lock", "Pipfile.lock", "tsconfig.json", "tsconfig.node.json", "tsconfig.app.json"}
# Placeholder / test / library-author emails that must never be treated as real contacts.
JUNK_EMAIL_RE = re.compile(
    r"^(test|demo|sample|user|username|name|you|your|yourname|email|info@example|admin@example|john|jane|"
    r"someone|me|foo|bar|abc|xyz)@|@(test|example|domain|email|company|yourcompany|yourdomain|mysite|"
    r"site|sentry|wixpress|izs)\.|\.(png|jpe?g|gif|webp|svg|css|js)$|noreply|no-reply|donotreply|@\d|"
    r"@2x\.|u00",
    re.I,
)
# Values that look like unfilled template placeholders.
PLACEHOLDER_RE = re.compile(
    r"x{4,}|X{4,}|\b20XX\b|\b19XX\b|\byour (full |street |business )?(address|name|city|company|email|phone)\b|"
    r"\b(lorem|ipsum|tbd|todo|placeholder|n/?a|fill (me|in))\b|<[^>]+>|\[[^\]]+\]|^\s*$",
    re.I,
)
# Social sites that block bots: a 4xx/999 from them means "couldn't verify", not "broken".
BOT_WALLED = ("linkedin.com", "instagram.com", "facebook.com", "x.com", "twitter.com", "tiktok.com",
              "quora.com", "medium.com", "indiamart.com", "justdial.com", "glassdoor")
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")
BROWSER_HEADERS = {"User-Agent": BROWSER_UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                   "Accept-Language": "en;q=0.9,*;q=0.5"}


def _clean_emails(emails) -> list[str]:
    out = []
    for e in emails:
        e = e.strip().strip(".").lower()
        if e and not JUNK_EMAIL_RE.search(e) and e not in out:
            out.append(e)
    return out


def _is_placeholder(v) -> bool:
    return isinstance(v, str) and bool(PLACEHOLDER_RE.search(v))


def _brand_words(name: str | None, domain: str = "") -> set[str]:
    words = set(re.findall(r"[a-z]{3,}", (name or "").lower()))
    stem = domain.split(".")[0] if domain else ""
    if stem:
        words.add(stem)
    return words


# ----------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _domain(url: str) -> str:
    d = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    return d[4:] if d.startswith("www.") else d


def _norm(url: str) -> str:
    url = urldefrag(url)[0]
    p = urlparse(url)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc.lower()}{path}" + (f"?{p.query}" if p.query else "")


def _keywords(text: str, n: int = 15, exclude: set[str] | None = None) -> list[str]:
    ex = STOP | (exclude or set())
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower()) if w not in ex]
    uni = Counter(words)
    bi = Counter(f"{a} {b}" for a, b in zip(words, words[1:]) if a != b)
    scored = [(k, v * 2.5) for k, v in bi.items() if v > 1] + list(uni.items())
    out, seen = [], set()
    for k, _ in sorted(scored, key=lambda x: -x[1]):
        if k not in seen:
            out.append(k)
            seen.add(k)
        if len(out) >= n:
            break
    return out


def _load(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def _save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


# ----------------------------------------------------------------- user data: custom.json + projects
def _custom() -> dict:
    """~/.backlink-mcp/custom.json - your own directories, footprints, templates and category hints.
    Merged with the built-ins at call time, so package updates never overwrite them."""
    c = _load(CUSTOM, {}) or {}
    return c if isinstance(c, dict) else {}


def _all_directories() -> list[dict]:
    seen, out = set(), []
    for d in (_custom().get("directories") or []) + DIRECTORIES:  # custom first: yours win on name clash
        if isinstance(d, dict) and d.get("name") and d.get("url") and d["name"].lower() not in seen:
            seen.add(d["name"].lower())
            out.append({"tags": ["general"], "region": "global", "priority": 3, "notes": "", **d})
    return out


def _all_footprints() -> dict[str, list[str]]:
    fp = {k: list(v) for k, v in FOOTPRINTS.items()}
    for group, qs in (_custom().get("footprints") or {}).items():
        fp.setdefault(group, [])
        fp[group] = list(qs) + [q for q in fp[group] if q not in qs]
    return fp


def _all_templates() -> dict:
    return {**OUTREACH_TEMPLATES, **(_custom().get("outreach_templates") or {})}


def _all_category_hints() -> list:
    extra = [(tuple(h[0]) if isinstance(h[0], list) else (h[0],), h[1]) for h in (_custom().get("category_hints") or [])
             if isinstance(h, list) and len(h) == 2]
    return extra + CATEGORY_HINTS


def _projects() -> dict:
    return _load(PROJECTS, {}) or {}


def _project(site: str | None) -> dict:
    return _projects().get(_domain(site), {}) if site else {}


def _jsonld(soup: BeautifulSoup) -> list[dict]:
    items = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if "@graph" in d:
                    stack.extend(d["@graph"])
                items.append(d)
    return items


def _parse_page(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    meta = lambda **kw: (soup.find("meta", attrs=kw) or {}).get("content")  # noqa: E731
    for t in soup(["script", "style", "noscript"]):
        if t.get("type") != "application/ld+json":
            t.decompose()
    text = " ".join(soup.get_text(" ").split())
    blocks, heading = [], None
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        if el.find_parent(["nav", "header", "footer", "aside", "form"]):
            continue
        t = " ".join(el.get_text(" ").split())
        if el.name in ("h1", "h2", "h3", "h4"):
            heading = t[:120] or heading
        elif len(t) >= 40 and not (el.name == "li" and el.find("p")):  # real body copy, not menu items
            blocks.append({"section": heading, "text": t[:1200], "tag": el.name,
                           "links_inside": len(el.find_all("a", href=True))})
        if len(blocks) >= 120:
            break
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        links.append({"href": _norm(urljoin(url, href)), "text": " ".join(a.get_text(" ").split())[:80],
                      "rel": " ".join(a.get("rel", [])),
                      "in_content": a.find_parent(["nav", "header", "footer", "aside"]) is None})
    canon = soup.find("link", rel="canonical")
    return {
        "url": url,
        "title": (soup.title.string.strip() if soup.title and soup.title.string else None),
        "meta_description": meta(name="description"),
        "canonical": canon.get("href") if canon else None,
        "robots": meta(name="robots"),
        "og": {k: meta(property=f"og:{k}") for k in ("title", "description", "image", "site_name")},
        "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")][:3],
        "h2": [h.get_text(" ", strip=True) for h in soup.find_all("h2")][:10],
        "lang": (soup.html.get("lang") if soup.html else None),
        "word_count": len(text.split()),
        "client_rendered": bool(soup.find(id=re.compile(r"^(root|app|__next|__nuxt|svelte)$")))
        and len(text.split()) < 80,
        "emails": _clean_emails(
            [a["href"][7:].split("?")[0] for a in soup.find_all("a", href=True) if a["href"].lower().startswith("mailto:")]
            + EMAIL_RE.findall(html))[:5],
        "tel_links": sorted({a["href"][4:] for a in soup.find_all("a", href=True) if a["href"].startswith("tel:")})[:5],
        "jsonld_types": sorted({str(d.get("@type")) for d in _jsonld(soup) if d.get("@type")}),
        "jsonld": _jsonld(soup)[:5],
        "links": links,
        "text_sample": text[:4000],
        "blocks": blocks,
    }


# ----------------------------------------------------------------- crawler
async def _crawl(start: str, max_pages: int) -> dict:
    start = start if "://" in start else "https://" + start
    dom = _domain(start)
    rp = urllib.robotparser.RobotFileParser()
    pages, broken, queue, seen = {}, [], [_norm(start)], set()
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as c:
        try:
            r = await c.get(urljoin(start, "/robots.txt"))
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            robots_txt = r.text[:2000] if r.status_code == 200 else None
        except Exception:
            rp.parse([])
            robots_txt = None
        try:
            sm = await c.get(urljoin(start, "/sitemap.xml"))
            sitemap_urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm.text) if sm.status_code == 200 else []
        except Exception:
            sitemap_urls = []
        for u in sitemap_urls[:max_pages]:
            if _domain(u) == dom and not u.endswith(".xml"):
                queue.append(_norm(u))
        while queue and len(pages) < max_pages:
            batch = []
            while queue and len(batch) < 5:
                u = queue.pop(0)
                if u not in seen and rp.can_fetch(UA, u):
                    seen.add(u)
                    batch.append(u)
            if not batch:
                continue
            res = await asyncio.gather(*(c.get(u) for u in batch), return_exceptions=True)
            for u, r in zip(batch, res):
                if isinstance(r, Exception):
                    broken.append({"url": u, "error": type(r).__name__})
                    continue
                if r.status_code >= 400:
                    broken.append({"url": u, "status": r.status_code})
                    continue
                if "html" not in r.headers.get("content-type", ""):
                    continue
                p = _parse_page(str(r.url), r.text)
                p["status"] = r.status_code
                pages[_norm(str(r.url))] = p
                for l in p["links"]:
                    if _domain(l["href"]) == dom and l["href"] not in seen and not re.search(
                        r"\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|mp4|css|js)$", l["href"], re.I):
                        queue.append(l["href"])
        # check a sample of external links for broken outbound links
        found_on = Counter(l["href"] for p in pages.values() for l in {x["href"]: x for x in p["links"]}.values()
                           if _domain(l["href"]) != dom and l["href"].startswith("http"))
        ext = [u for u, _ in found_on.most_common(60)]

        async def _check(u: str):
            try:
                r = await c.head(u, headers=BROWSER_HEADERS)
                if r.status_code in (403, 405, 429, 501, 999) or r.status_code >= 400:
                    r = await c.get(u, headers=BROWSER_HEADERS)
                return r.status_code
            except Exception as e:  # noqa: BLE001
                return type(e).__name__

        res = await asyncio.gather(*(_check(u) for u in ext))
        broken_out, unverified_out = [], []
        for u, st in zip(ext, res):
            if isinstance(st, int) and st < 400:
                continue
            item = {"url": u, "status": st, "found_on_pages": found_on[u]}
            walled = any(b in _domain(u) for b in BOT_WALLED)
            # Bot-walled sites answer 999/403/429 to everyone; only a clean 404/410 there is meaningful.
            if walled and st not in (404, 410):
                item["note"] = "site blocks bots - open it in a browser to confirm"
                unverified_out.append(item)
            else:
                if walled:
                    item["note"] = "social sites sometimes 404 for bots - confirm in a browser"
                broken_out.append(item)
    return {"domain": dom, "start": start, "pages": pages, "broken_internal": broken,
            "broken_outbound": broken_out, "unverified_outbound": unverified_out, "robots_txt": robots_txt,
            "sitemap_found": bool(sitemap_urls), "sitemap_count": len(sitemap_urls), "scanned_at": _now()}


def _profile_from_pages(pages: dict, domain: str) -> dict:
    org, all_text = {}, ""
    emails, phones = Counter(), Counter()
    for p in pages.values():
        all_text += " ".join(filter(None, [p["title"], p["meta_description"], *p["h1"], *p["h2"]])) + " "
        emails.update(p["emails"])
        phones.update(p["tel_links"])
        for d in p["jsonld"]:
            t = str(d.get("@type", ""))
            if any(k in t for k in ("Organization", "LocalBusiness", "Corporation", "Store", "Restaurant")):
                org = org or d
    home = next(iter(pages.values()), {})
    addr = org.get("address", {}) if isinstance(org.get("address"), dict) else {}
    name = (org.get("name") or (home.get("og") or {}).get("site_name")
            or re.split(r"\s[|\-–—:]\s", home.get("title") or domain)[0].strip())
    return {
        "name": name,
        "website": f"https://{domain}",
        "description": org.get("description") or home.get("meta_description"),
        "email": org.get("email") or (emails.most_common(1)[0][0] if emails else None),
        "phone": org.get("telephone") or (phones.most_common(1)[0][0] if phones else None),
        "address": {k: addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")} if addr else None,
        "logo": org.get("logo") if isinstance(org.get("logo"), str) else (org.get("logo") or {}).get("url"),
        "same_as": org.get("sameAs", []),
        "keywords": _keywords(all_text, 20, _brand_words(name, domain)),
        "schema_types": sorted({str(d.get("@type")) for p in pages.values() for d in p["jsonld"] if d.get("@type")}),
    }


# ----------------------------------------------------------------- tools: scanning
@mcp.tool()
async def scan_site(url: str, max_pages: int = 30) -> dict:
    """Crawl a live website (respects robots.txt, reads sitemap.xml) and return a business profile
    (name, contact, address, keywords, social profiles), per-page SEO data, broken links and link stats.
    Results are cached for the other tools."""
    data = await _crawl(url, max(1, min(max_pages, 200)))
    profile = _profile_from_pages(data["pages"], data["domain"])
    _save(CACHE / f"{data['domain']}.json", {**data, "profile": profile})
    projects = _projects()
    if data["domain"] not in projects:  # remember the site; save_project fills in niche/location/country
        country = resolve_country((profile.get("address") or {}).get("addressCountry"))
        projects[data["domain"]] = {"site": data["domain"], "name": profile.get("name"),
                                    "keywords": profile.get("keywords", [])[:6], "country": country,
                                    "location": (profile.get("address") or {}).get("addressLocality"),
                                    "created": _now(), "updated": _now(), "auto": True}
        _save(PROJECTS, projects)
    dom = data["domain"]
    ext = Counter(_domain(l["href"]) for p in data["pages"].values() for l in p["links"] if _domain(l["href"]) != dom)
    return {
        "profile": profile,
        "pages_scanned": len(data["pages"]),
        "sitemap_found": data["sitemap_found"],
        "robots_txt_found": data["robots_txt"] is not None,
        "pages": [{k: p[k] for k in ("url", "title", "meta_description", "h1", "word_count", "jsonld_types")}
                  for p in data["pages"].values()],
        "broken_internal": data["broken_internal"],
        "broken_outbound": data["broken_outbound"],
        "unverified_outbound": data.get("unverified_outbound", []),
        "client_rendered_pages": [p["url"] for p in data["pages"].values() if p.get("client_rendered")],
        "top_outbound_domains": ext.most_common(15),
        "profiles_linked_from_site": sorted({d for d in ext if any(s in d for s in (
            "linkedin", "facebook", "instagram", "twitter", "x.com", "youtube", "github", "justdial",
            "indiamart", "clutch", "goodfirms", "google", "behance", "dribbble"))}),
        "project": _project(data["domain"]),
        "next": "Run save_project (niche, location, country) if not done, then seo_link_audit and find_opportunities.",
    }


@mcp.tool()
def scan_codebase(path: str, max_files: int = 3000, site: str = "") -> dict:
    """Scan a local website project (React/Vite, Next.js, Django, plain HTML, etc.): detect framework,
    routes/pages, meta tags, sitemap/robots, structured data, contact details and external links.
    Use when the site isn't live yet or to find what to fix in code. Pass site= (e.g. "example.com") to remember
    this folder for that project, so internal_link_suggestions and content_plan can point to exact files/lines."""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"error": f"Not a directory: {root}"}
    if site:
        projects = _projects()
        pr = projects.get(_domain(site), {"site": _domain(site), "created": _now()})
        pr["code_path"] = str(root)
        pr["updated"] = _now()
        projects[_domain(site)] = pr
        _save(PROJECTS, projects)
    framework, deps = [], {}
    pkg = root / "package.json"
    if pkg.exists():
        j = _load(pkg, {})
        deps = {**j.get("dependencies", {}), **j.get("devDependencies", {})}
        for k, name in [("next", "Next.js"), ("react-router-dom", "React Router"), ("vite", "Vite"),
                        ("gatsby", "Gatsby"), ("astro", "Astro"), ("nuxt", "Nuxt"), ("@sveltejs/kit", "SvelteKit"),
                        ("react-helmet", "react-helmet"), ("react-helmet-async", "react-helmet-async"),
                        ("next-sitemap", "next-sitemap"), ("i18next", "i18next")]:
            if k in deps:
                framework.append(name)
    if (root / "manage.py").exists():
        framework.append("Django")
    reqs = root / "requirements.txt"
    if reqs.exists() and "fastapi" in reqs.read_text(errors="ignore").lower():
        framework.append("FastAPI")

    routes, titles, descs, ext_links, emails, phones = set(), set(), set(), Counter(), Counter(), set()
    route_files: dict[str, set[str]] = defaultdict(set)
    social_links: dict[str, set[str]] = defaultdict(set)
    files_with_jsonld, files_with_meta, sitemap, robots, text_blob, n = [], [], [], [], "", 0
    for f in root.rglob("*"):
        if n >= max_files:
            break
        if (any(part in SKIP_DIRS for part in f.parts) or not f.is_file() or f.suffix.lower() not in CODE_EXT
                or f.name in SKIP_FILES or f.name.endswith((".min.js", ".map", ".d.ts"))):
            continue
        if f.stat().st_size > 800_000:
            continue
        n += 1
        rel = str(f.relative_to(root))
        name = f.name.lower()
        if "sitemap" in name:
            sitemap.append(rel)
        if name.startswith("robots"):
            robots.append(rel)
        src = f.read_text("utf-8", errors="ignore")
        # Next.js file routing
        m = re.match(r"(?:src/)?(app|pages)/(.*)", rel.replace("\\", "/"))
        if m and re.search(r"(page|index)?\.(t|j)sx?$|\.mdx?$", name) and "/api/" not in rel and not name.startswith("_"):
            r = re.sub(r"/?(page|index)?\.(tsx|jsx|ts|js|mdx|md)$", "", m.group(2))
            r = re.sub(r"\([^)]*\)/?", "", r)  # route groups
            routes.add("/" + r.strip("/"))
        for rt in re.findall(r"""path\s*[:=]\s*["'](/[^"']*)["']""", src):  # react-router
            routes.add(rt)
            route_files[rt].add(rel)
        routes.update("/" + p for p in re.findall(r"""(?:re_)?path\(\s*r?["']\^?([^"'$]*)""", src) if f.suffix == ".py")
        titles.update(t.strip() for t in re.findall(r"<title[^>]*>([^<{]{3,120})</title>", src))
        titles.update(re.findall(r"""title\s*:\s*["'`]([^"'`]{3,120})["'`]""", src) if "metadata" in src or "Helmet" in src else [])
        descs.update(re.findall(r"""name=["']description["']\s+content=["']([^"']{10,300})""", src))
        descs.update(re.findall(r"""description\s*:\s*["'`]([^"'`]{20,300})["'`]""", src) if "metadata" in src else [])
        if "application/ld+json" in src or '"@context"' in src:
            files_with_jsonld.append(rel)
        if re.search(r'og:title|twitter:card|<Helmet|export const metadata|generateMetadata', src):
            files_with_meta.append(rel)
        for u in re.findall(r"""https?://[^\s"'`<>)]+""", src):
            if any(b in _domain(u) for b in BOT_WALLED + ("youtube.com", "github.com")):
                social_links[u.rstrip("/.,;")].add(rel)
            if not re.search(r"(schema\.org|w3\.org|googleapis|gstatic|cdn|unpkg|jsdelivr|npmjs|localhost|127\.0\.0\.1|example\.com|github\.com/[^/]+/[^/]+/(blob|issues))", u):
                ext_links[_domain(u)] += 1
        emails.update(_clean_emails(EMAIL_RE.findall(src)))
        phones.update(re.findall(r"tel:([+\d\s-]{8,})", src))
        if f.suffix.lower() in {".html", ".tsx", ".jsx", ".md", ".mdx", ".vue", ".astro"}:
            text_blob += " " + re.sub(r"<[^>]+>|\{[^}]*\}|import .*|export .*", " ", src)[:5000]

    issues = []
    if not sitemap:
        issues.append("No sitemap file/generator found - add one (e.g. next-sitemap / vite-plugin-sitemap / django.contrib.sitemaps).")
    if not robots:
        issues.append("No robots.txt found - add one that references the sitemap.")
    if not files_with_jsonld:
        issues.append("No JSON-LD structured data - add Organization/LocalBusiness schema (helps citations & knowledge panel).")
    if not files_with_meta:
        issues.append("No per-page meta/OpenGraph handling found - shared links will preview poorly.")
    if "Vite" in framework and "Next.js" not in framework and not any(x in deps for x in ("vite-plugin-ssr", "vike", "vite-ssg", "react-snap")):
        issues.append("Client-only SPA (Vite) - consider prerendering (vite-ssg/vike/react-snap) so crawlers and link-preview bots see content.")
    # routes that differ only by case (/About vs /about) split link equity and can 404 on case-sensitive hosts
    by_lower = defaultdict(set)
    for rt in routes:
        by_lower[rt.lower().rstrip("/") or "/"].add(rt)
    case_dupes = {k: sorted(v) for k, v in by_lower.items() if len(v) > 1}
    upper_routes = sorted(rt for rt in routes if rt != rt.lower() and ":" not in rt)
    if case_dupes:
        issues.append(f"Routes differing only by case: {case_dupes} - keep one lowercase URL and 301 the others.")
    elif upper_routes:
        issues.append(f"Routes with uppercase letters: {upper_routes[:8]} - use lowercase URLs (and match the sitemap).")
    linkedin = sorted(u for u in social_links if "linkedin.com" in u)
    if len({re.sub(r"https?://([a-z]{2}\.)?(www\.)?", "", u) for u in linkedin}) > 1:
        issues.append(f"Different LinkedIn URLs used across the code: {linkedin} - use one canonical URL everywhere.")
    return {
        "root": str(root), "files_scanned": n, "framework": framework or ["unknown/static"],
        "routes": sorted(routes)[:200], "titles": sorted(titles)[:40], "descriptions": sorted(descs)[:20],
        "sitemap_files": sitemap, "robots_files": robots, "jsonld_files": files_with_jsonld[:20],
        "meta_files": files_with_meta[:20],
        "emails": [e for e, _ in emails.most_common(10)], "phones": sorted(phones)[:5],
        "social_links": {u: sorted(f)[:5] for u, f in sorted(social_links.items())[:30]},
        "case_duplicate_routes": case_dupes,
        "external_domains": ext_links.most_common(30), "keywords": _keywords(text_blob, 20),
        "issues": issues,
        "tip": "social_links shows which files contain each profile URL - fix broken ones there.",
    }


@mcp.tool()
def seo_link_audit(domain: str) -> dict:
    """Audit the cached scan_site result for problems that waste or block link equity: missing titles/
    descriptions/canonicals, noindex, thin pages, missing schema/OG, broken links, orphan pages.
    Run scan_site first."""
    d = _load(CACHE / f"{_domain(domain)}.json", None)
    if not d:
        return {"error": "No scan cached. Run scan_site first."}
    pages, dom = d["pages"], d["domain"]
    inbound = Counter(l["href"] for p in pages.values() for l in p["links"] if _domain(l["href"]) == dom)
    issues = defaultdict(list)
    titles = Counter(p["title"] for p in pages.values())
    for u, p in pages.items():
        if not p["title"]:
            issues["missing_title"].append(u)
        elif titles[p["title"]] > 1:
            issues["duplicate_title"].append(u)
        if not p["meta_description"]:
            issues["missing_meta_description"].append(u)
        if not p["canonical"]:
            issues["missing_canonical"].append(u)
        if p["robots"] and "noindex" in p["robots"].lower():
            issues["noindex"].append(u)
        if not p["h1"]:
            issues["missing_h1"].append(u)
        if p["word_count"] < 250:
            issues["thin_content(<250 words)"].append(u)
        if not p["og"].get("title") or not p["og"].get("image"):
            issues["missing_og_tags"].append(u)
        if inbound[u] <= 1 and u != _norm(d["start"]):
            issues["weak_internal_links(<=1 inbound)"].append(u)
    site_wide = []
    if not d["sitemap_found"]:
        site_wide.append("sitemap.xml not found")
    if d["robots_txt"] is None:
        site_wide.append("robots.txt not found")
    if not any(p["jsonld_types"] for p in pages.values()):
        site_wide.append("No structured data (JSON-LD) on any page")
    prof = d["profile"]
    if not (prof.get("phone") and prof.get("address")):
        site_wide.append("Name/Address/Phone not machine-readable - add LocalBusiness schema; NAP must match every citation exactly")
    linkable = sorted(pages.values(), key=lambda p: -p["word_count"])[:5]

    # Ranked, de-duplicated fix list: (impact, text). Higher impact first.
    fixes: list[tuple[int, str]] = []
    if issues.get("noindex"):
        fixes.append((100, f"Remove noindex from {len(issues['noindex'])} page(s): {issues['noindex'][:5]}"))
    for b in sorted(d.get("broken_outbound", []), key=lambda x: -x.get("found_on_pages", 1)):
        if b.get("found_on_pages", 1) >= 3:
            fixes.append((90, f"Broken link {b['url']} (status {b['status']}) on {b['found_on_pages']} pages"
                              + (f" - {b['note']}" if b.get("note") else "")))
    if d["broken_internal"]:
        fixes.append((85, f"Fix {len(d['broken_internal'])} broken internal link(s): {[x['url'] for x in d['broken_internal'][:5]]}"))
    types = {t for p in pages.values() for t in p["jsonld_types"]}
    if not any("LocalBusiness" in t or t in ("ProfessionalService", "Store", "Restaurant", "Hotel") for t in types):
        fixes.append((80, "No LocalBusiness schema - run generate_schema and paste the output into index.html <head>"
                          + ("" if (prof.get("address") or {}).get("streetAddress") else
                             "; you also need a street address on the site (Google Business Profile & most directories require it)")))
    if not prof.get("same_as"):
        fixes.append((50, "No sameAs social links in schema - add your LinkedIn/GitHub/Facebook URLs (generate_schema does this)"))
    spa = [p["url"] for p in pages.values() if p.get("client_rendered")]
    if spa:
        fixes.append((75, f"{len(spa)} page(s) render only in JavaScript - prerender them (vite-ssg / react-snap / Next.js) so bots see content"))
    if not d["sitemap_found"]:
        fixes.append((70, "Add sitemap.xml and reference it in robots.txt"))
    if issues.get("missing_canonical"):
        fixes.append((45, f"Add canonical tags to {len(issues['missing_canonical'])} page(s)"))
    if issues.get("missing_meta_description"):
        fixes.append((40, f"Write meta descriptions for {len(issues['missing_meta_description'])} page(s)"))
    if issues.get("thin_content(<250 words)"):
        fixes.append((35, f"Expand thin pages: {issues['thin_content(<250 words)'][:6]}"))
    if issues.get("weak_internal_links(<=1 inbound)"):
        fixes.append((30, "Strengthen internal links to weak pages - see internal_link_suggestions"))
    if issues.get("missing_og_tags"):
        fixes.append((20, f"Add og:title/og:image to {len(issues['missing_og_tags'])} page(s) for better link previews"))
    return {
        "priority_fixes": [t for _, t in sorted(fixes, key=lambda x: -x[0])],
        "site_wide": site_wide,
        "page_issues": {k: v[:25] for k, v in issues.items()},
        "broken_internal": d["broken_internal"],
        "broken_outbound": d["broken_outbound"],
        "unverified_outbound": d.get("unverified_outbound", []),
        "most_linkable_pages": [{"url": p["url"], "title": p["title"], "words": p["word_count"]} for p in linkable],
        "tip": "Fix noindex/broken/canonical issues before outreach - links to broken or noindexed pages are wasted.",
    }


GENERIC_ANCHORS = {"software", "services", "service", "solutions", "solution", "company", "business", "businesses",
                   "team", "products", "product", "system", "systems", "app", "apps", "website", "online", "quality",
                   "best", "work", "help", "support", "more", "click", "here", "read", "learn", "page", "home"}
SERVICE_SECTION_RE = re.compile(r"what we (do|build|offer|make)|services|solutions|products|our work|how we help|expertise", re.I)

TEXT_EXT = {".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro", ".md", ".mdx", ".php",
            ".py", ".json", ".yaml", ".yml", ".txt", ".liquid", ".hbs", ".njk", ".ejs"}


def _code_files(root: str | None, limit: int = 4000) -> list[Path]:
    if not root or not Path(root).is_dir():
        return []
    out = []
    for f in Path(root).rglob("*"):
        if len(out) >= limit:
            break
        if (f.is_file() and f.suffix.lower() in TEXT_EXT and not any(part in SKIP_DIRS for part in f.parts)
                and f.name not in SKIP_FILES and not f.name.endswith((".min.js", ".map", ".d.ts"))
                and f.stat().st_size < 600_000):
            out.append(f)
    return out


def _find_in_code(files: list[Path], root: str | None, text: str, anchor: str = "") -> list[dict]:
    """Locate a sentence from the live page in the source code. Tries a few word-runs around the anchor,
    allowing any whitespace/JSX line breaks between words. Returns [{file, line}]."""
    if not files or not text:
        return []
    words = re.findall(r"[\w'’-]+", text)
    if len(words) < 3:
        return []
    idx = 0
    if anchor:
        aw = anchor.lower().split()
        for i in range(len(words)):
            if [w.lower() for w in words[i:i + len(aw)]] == aw:
                idx = i
                break
    runs = []
    for size in (7, 5, 4):
        start = max(0, min(idx - 2, len(words) - size))
        if len(words) >= size:
            runs.append(words[start:start + size])
    if len(words) >= 5:
        runs.append(words[:5])
    for run in runs:
        pat = re.compile(r"[\s\S]{0,12}?".join(re.escape(w) for w in run), re.I)
        hits = []
        for f in files:
            try:
                src = f.read_text("utf-8", errors="ignore")
            except OSError:
                continue
            m = pat.search(src)
            if m:
                hits.append({"file": str(f.relative_to(root)) if root else str(f),
                             "line": src.count("\n", 0, m.start()) + 1})
            if len(hits) >= 3:
                break
        if hits:
            return hits
    return []


def _sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])", text) if len(x.strip()) > 15]


def _path(url: str) -> str:
    p = urlparse(url)
    return (p.path or "/") + (f"?{p.query}" if p.query else "")


def _page_kind(url: str, page: dict) -> str:
    t = (_path(url) + " " + (page.get("title") or "") + " " + " ".join(page.get("h1") or [])).lower()
    if _path(url) in ("/", ""):
        return "home"
    for kind, keys in (("contact", ("contact", "get in touch", "reach us")), ("about", ("about", "our story", "team")),
                       ("pricing", ("pricing", "plans", "price")), ("careers", ("career", "jobs", "hiring")),
                       ("blog_index", ("/blog", "/insights", "/news", "/articles", "/resources")),
                       ("case_study", ("case-stud", "case stud", "portfolio", "/work")),
                       ("faq", ("faq", "questions"))):
        if any(k in t for k in keys):
            if kind == "blog_index" and len([x for x in _path(url).split("/") if x]) > 1:
                return "article"
            return kind
    if any(k in t for k in ("/blog/", "/insights/", "/news/", "/article", "how to", "guide", "what is", "why ")):
        return "article"
    return "service"


@mcp.tool()
def internal_link_suggestions(domain: str, limit: int = 20) -> list[dict]:
    """Suggest in-content (contextual) internal links for weakly-linked pages and say EXACTLY where to put each:
    the page, the section heading, the paragraph and sentence, the anchor text, a ready-made edited sentence
    with the link, and - if the site's code folder is known (scan_codebase with site=, or save_project code_path=)
    - the file and line to edit. When no existing sentence fits, it proposes a new sentence and the best section
    to add it to (marked placement="add_sentence"; reword it in your own voice). Run scan_site first."""
    d = _load(CACHE / f"{_domain(domain)}.json", None)
    if not d:
        return [{"error": "No scan cached. Run scan_site first."}]
    pages, dom = d["pages"], d["domain"]
    if not any(p.get("blocks") for p in pages.values()):
        return [{"error": "This scan is from an older version without paragraph data. Run scan_site again."}]
    proj = _project(dom)
    root = proj.get("code_path")
    files = _code_files(root)
    inbound = Counter(l["href"] for p in pages.values() for l in p["links"] if _domain(l["href"]) == dom)
    brand = set(re.findall(r"[a-z]+", (d.get("profile", {}).get("name") or "").lower())) | _brand_words(None, dom)
    title_words = Counter(w for p in pages.values() for w in set(re.findall(r"[a-z]+", (p["title"] or "").lower())))
    common = {w for w, c in title_words.items() if c > len(pages) * 0.6} if len(pages) >= 5 else set()
    out, used_sentences = [], set()
    for tu, tp in sorted(pages.items(), key=lambda kv: inbound[kv[0]]):
        if len(out) >= limit:
            break
        if _page_kind(tu, tp) == "home" or (_page_kind(tu, tp) in ("contact", "careers") and inbound[tu] >= 2):
            continue
        src_text = " ".join(filter(None, [tp["title"], *tp["h1"], *tp.get("h2", [])[:3], tp["meta_description"]]))
        kws = [k for k in _keywords(src_text, 12, brand | common)
               if (len(k) > 3 or k in ACRONYMS) and not (len(k.split()) == 1 and k in GENERIC_ANCHORS)]
        kws = sorted(kws, key=lambda k: (-len(k.split()), -len(k)))[:6]  # descriptive multi-word anchors first
        if not kws:
            continue
        # menu/footer links don't count - a link inside body copy is what passes relevance
        linked_from = {su for su, sp in pages.items()
                       if any(l["href"] == tu and l.get("in_content", True) for l in sp["links"])}
        picks, best_fallback = 0, None
        for su, sp in sorted(pages.items(), key=lambda kv: -inbound[kv[0]]):  # strongest pages first
            if su == tu or su in linked_from or picks >= 3:
                continue
            found, shared = None, None
            # prefer paragraphs that don't already have links in them, then any paragraph
            for blk in sorted(sp.get("blocks", []), key=lambda b: (b["links_inside"] > 1, b["tag"] != "p")):
                for k in kws:
                    m = re.search(rf"\b{re.escape(k)}\b", blk["text"], re.I)
                    if m:
                        sent = next((x for x in _sentences(blk["text"]) if m.group(0).lower() in x.lower()), blk["text"])
                        if (su, sent) in used_sentences:  # prefer a sentence that isn't getting another link
                            shared = shared or (blk, m.group(0), sent)
                            continue
                        found = (blk, m.group(0), sent)
                        break
                if found:
                    break
            found = found or shared
            if found:
                blk, anchor, sent = found
                is_shared = (su, sent) in used_sentences
                used_sentences.add((su, sent))
                linked = re.sub(re.escape(anchor), f'<a href="{_path(tu)}">{anchor}</a>', sent, count=1)
                out.append({
                    "placement": "existing_text",
                    "add_link_on_page": su, "link_to": tu, "anchor_text": anchor,
                    "section": blk["section"] or "(top of page)",
                    "paragraph": _cut(blk["text"], 320),
                    "sentence": sent,
                    "sentence_with_link": linked,
                    "code_location": _find_in_code(files, root, sent, anchor),
                    "target_inbound_links_now": inbound[tu],
                    "note": ("This sentence also gets another suggested link - keep the more important one or "
                             "split the sentence." if is_shared else
                             "Already in the menu, but a link inside body text is stronger." if su in
                             {x for x, xp in pages.items() if any(l["href"] == tu for l in xp["links"])} else None),
                })
                picks += 1
            elif best_fallback is None and sp.get("blocks"):
                # the most related paragraph on this page - or its services-type section - for a new sentence
                tw = set(" ".join(kws).split()) - GENERIC_ANCHORS
                score = lambda b: len(tw & set(re.findall(r"[a-z]+", b["text"].lower())))  # noqa: E731
                blk = max(sp["blocks"], key=score)
                if score(blk) >= 1:
                    best_fallback = (su, blk)
                elif _page_kind(su, sp) in ("home", "service", "about"):
                    svc = [b for b in sp["blocks"] if b.get("section") and SERVICE_SECTION_RE.search(b["section"])]
                    if svc:
                        best_fallback = (su, svc[-1])
        if picks == 0 and best_fallback and _page_kind(tu, tp) in ("service", "article", "case_study", "pricing"):
            su, blk = best_fallback
            kind = _page_kind(tu, tp)
            label = (tp["h1"][0] if tp.get("h1") else (tp["title"] or kws[0]).split("|")[0].strip())
            label = label[0].lower() + label[1:] if kind == "service" and label[:2].isalpha() and not label[:2].isupper() else label
            sentence = (f'For a deeper look, read our guide: <a href="{_path(tu)}">{label}</a>.' if kind == "article"
                        else f'See how we help with <a href="{_path(tu)}">{label}</a>.' if kind == "service"
                        else f'You can find more on our <a href="{_path(tu)}">{label}</a> page.')
            out.append({
                "placement": "add_sentence",
                "add_link_on_page": su, "link_to": tu, "anchor_text": label,
                "section": blk["section"] or "(top of page)",
                "add_after_paragraph": _cut(blk["text"], 320),
                "suggested_sentence": sentence,
                "note": "No existing sentence mentions this topic - add this line (reworded in your voice) "
                        "at the end of the paragraph above.",
                "code_location": _find_in_code(files, root, blk["text"]),
                "target_inbound_links_now": inbound[tu],
            })
    if not root:
        out.append({"tip": "Run scan_codebase with site= (or save_project code_path=) to get the exact file and line for each edit."})
    return out[:limit + (0 if root else 1)]


SECTION_PLANS = {
    "home": [("What we do", "2-3 sentences: who you help and the main result you deliver."),
             ("Services", "One short paragraph per main service, each linking to its own page."),
             ("Why choose us", "3-4 concrete reasons with numbers or proof (years, projects, reviews)."),
             ("Recent work / case studies", "1-2 short examples with the client's industry and outcome."),
             ("Areas we serve", "Your city/region and the places you work in (helps local SEO)."),
             ("FAQ", "3-5 questions customers actually ask, with short answers.")],
    "service": [("What it is", "Plain-language explanation of the service/product and who it's for."),
                ("Problems it solves", "The pain points of the customer, in their words."),
                ("Features / what's included", "Bulleted list, each with one line of explanation."),
                ("How it works / our process", "3-5 steps from first call to delivery."),
                ("Results / example", "A real example or case study with numbers if you have them."),
                ("FAQ", "Pricing range, timelines, support, integrations - whatever people ask."),
                ("Call to action", "One clear next step with a link to the contact page.")],
    "contact": [("Contact details", "Business name, full street address, phone and email as visible text "
                                    "(exactly matching your directory listings)."),
                ("Opening hours", "Days and times, including weekends/holidays."),
                ("How to find us", "Landmark directions, parking, and an embedded map."),
                ("What happens next", "What you'll do after they get in touch and how fast you reply."),
                ("Areas we serve", "City/region served, for local search.")],
    "about": [("Our story", "When and why the business started, in a few honest sentences."),
              ("What we believe / how we work", "Your approach, in concrete terms."),
              ("Team", "Founder/key people with a line each (photos help trust)."),
              ("Milestones / proof", "Clients served, projects, awards, certifications - real facts only."),
              ("Where we are", "Location and areas served, linking to the contact page.")],
    "blog_index": [("Intro", "2-3 sentences on what readers will learn here and who it's for."),
                   ("Topic sections", "Group posts under 2-4 topic headings with a one-line summary each."),
                   ("Start here", "Link your 2-3 best guides with a sentence on why to read each.")],
    "article": [("Key takeaways", "A 3-bullet summary at the top."),
                ("Step-by-step / examples", "Practical detail and real examples - the part people link to."),
                ("Common mistakes", "What to avoid and why."),
                ("Related services", "A short paragraph linking to the matching service page."),
                ("FAQ", "2-4 follow-up questions.")],
    "case_study": [("The client", "Industry, size, location."), ("The challenge", "What wasn't working."),
                   ("What we did", "Approach and solution."), ("Results", "Numbers: time saved, revenue, errors cut."),
                   ("Quote", "A real quote from the client, with permission.")],
    "pricing": [("What's included", "Per plan, in plain words."), ("How pricing works", "What changes the price."),
                ("FAQ", "Payment terms, contracts, refunds, support.")],
    "faq": [("Grouped questions", "Group by topic (pricing, process, support) with 3-5 Q&As each.")],
    "careers": [("Why work here", "Culture and benefits, honestly."), ("Open roles", "Each role with a short summary.")],
}
TARGET_WORDS = {"home": 500, "service": 700, "contact": 250, "about": 400, "blog_index": 300, "article": 1000,
                "case_study": 500, "pricing": 350, "faq": 400, "careers": 300}


@mcp.tool()
def content_plan(domain: str, url: str = "", max_pages: int = 8) -> list[dict]:
    """Say what text (paragraphs/sections) to ADD to thin or weak pages and WHERE: page type, current vs target
    word count, the sections it already has, the sections/paragraphs to add (with what to write in each, which
    keywords fit naturally, and which internal links to include), where to insert them, and the source file if
    the code folder is known. Pass url= for one page, otherwise the thinnest pages are planned. Run scan_site
    first. Write the copy in your own words - never keyword-stuff."""
    d = _load(CACHE / f"{_domain(domain)}.json", None)
    if not d:
        return [{"error": "No scan cached. Run scan_site first."}]
    pages, dom = d["pages"], d["domain"]
    proj = _project(dom)
    root = proj.get("code_path")
    files = _code_files(root)
    proj_kws = [k for k in (proj.get("keywords") or []) if k]
    loc = proj.get("location")
    targets = [(u, p) for u, p in pages.items() if not url or _norm(u) == _norm(url) or _path(u) == _path(url)]
    if url and not targets:
        return [{"error": f"{url} isn't in the last scan. Run scan_site again or check the URL."}]
    scored = []
    for u, p in targets:
        kind = _page_kind(u, p)
        target = TARGET_WORDS.get(kind, 500)
        if url or p["word_count"] < target * 0.8:
            scored.append((p["word_count"] / target, u, p, kind, target))
    out = []
    for _, u, p, kind, target in sorted(scored)[:max_pages]:
        have = [h.lower() for h in (p.get("h2") or [])] + [b["section"].lower() for b in p.get("blocks", []) if b.get("section")]
        page_kws = _keywords(" ".join(filter(None, [p["title"], *p["h1"], p["meta_description"]])), 6,
                             _brand_words(d.get("profile", {}).get("name"), dom))
        add = []
        synonyms = {"faq": ("faq", "frequently asked", "questions"), "team": ("team", "people", "founder"),
                    "call to action": ("get started", "get in touch", "book", "talk to us")}
        for heading, what in SECTION_PLANS.get(kind, SECTION_PLANS["service"]):
            first = heading.lower().split(" / ")[0]
            keys = synonyms.get(first, (first,))
            if any(k in h for h in have for k in keys):
                continue
            if first == "contact details" and p.get("tel_links") and re.search(r"\d{5,6}|street|road|nagar|ave", p["text_sample"], re.I):
                continue
            item = {"heading": heading, "what_to_write": what}
            if heading in ("Areas we serve", "Where we are") and loc:
                item["what_to_write"] += f" Mention {loc} naturally."
            add.append(item)
        # internal links this page should carry
        rel_links = []
        for ou, op in pages.items():
            if ou == u or any(l["href"] == ou for l in p["links"]):
                continue
            if _page_kind(ou, op) in ("service", "article", "case_study") and set(page_kws) & set(
                    _keywords(" ".join(filter(None, [op["title"], *op["h1"]])), 8)):
                rel_links.append({"link_to": ou, "suggested_anchor": (op["h1"][0] if op.get("h1") else op["title"])})
        h1 = p["h1"][0] if p.get("h1") else None
        last_block = p["blocks"][-1]["text"] if p.get("blocks") else None
        out.append({
            "page": u, "page_type": kind, "words_now": p["word_count"], "target_words": target,
            "words_to_add": max(0, target - p["word_count"]),
            "headings_now": (p.get("h1") or []) + (p.get("h2") or []),
            "sections_to_add": add,
            "keywords_to_use_naturally": [] if kind in ("contact", "careers") else
            list(dict.fromkeys(page_kws[:3] + proj_kws[:2]))[:4],
            "where_to_insert": ("Add the new sections between the existing content and the footer, in the order "
                                "listed; keep the main call-to-action last." if p.get("blocks") else
                                "The page has almost no body text - add these sections under the main heading."),
            "internal_links_to_include": rel_links[:4],
            "code_location": _find_in_code(files, root, last_block or h1 or "", "") if (last_block or h1) else [],
            "rules": ["Write for people first: specific, useful, in your own voice.",
                      "Use each keyword once or twice where it fits - never stuff.",
                      "Only real facts (numbers, clients, reviews)."],
        })
    if not out:
        return [{"ok": True, "msg": "No thin pages found - every scanned page meets its target length."}]
    if not root:
        out.append({"tip": "Run scan_codebase with site= (or save_project code_path=) to get the file for each page."})
    return out


# ----------------------------------------------------------------- tools: opportunities
@mcp.tool()
def save_project(site: str, niche: str = "", location: str = "", country: str = "",
                 keywords: list[str] | None = None, competitors: list[str] | None = None,
                 business_name: str = "", notes: str = "", code_path: str = "") -> dict:
    """Save (or update) a site you're working on - your own or a client's - so every other tool knows its
    niche, location, country, keywords and competitors. Only the fields you pass are changed.
    country: name or code ("India", "IN", "UK", "United States"...)."""
    dom = _domain(site)
    projects = _projects()
    pr = projects.get(dom, {"site": dom, "created": _now()})
    code = resolve_country(country) if country else None
    if country and not code:
        return {"ok": False, "msg": f"Unknown country {country!r}. Use a name or ISO code, e.g. India/IN, UK/GB, US.",
                "known": sorted(COUNTRIES)}
    for k, v in (("niche", niche), ("location", location), ("country", code), ("keywords", keywords),
                 ("competitors", [_domain(c) for c in competitors] if competitors else None),
                 ("name", business_name), ("notes", notes),
                 ("code_path", str(Path(code_path).expanduser().resolve()) if code_path else None)):
        if v:
            pr[k] = v
    pr.pop("auto", None)
    pr["updated"] = _now()
    projects[dom] = pr
    _save(PROJECTS, projects)
    return {"ok": True, "project": pr}


@mcp.tool()
def list_projects() -> dict:
    """List every site you've scanned or saved, with niche, location, country and tracker progress."""
    tr = _load(TRACKER, [])
    out = []
    for dom, pr in sorted(_projects().items()):
        st = Counter(e["status"] for e in tr if e.get("site") == dom)
        out.append({**pr, "tracker": dict(st), "kit_saved": (DATA_DIR / f"submission_kit_{dom}.json").exists()})
    return {"count": len(out), "projects": out, "data_folder": str(DATA_DIR)}


def _niche_tags(niche: str) -> set[str]:
    n = f" {niche.lower()} "
    return {t for k, ts in NICHE_TAGS.items() if k in n for t in ts}


@mcp.tool()
def find_opportunities(niche: str = "", location: str = "", country: str = "",
                       keywords: list[str] | None = None, competitors: list[str] | None = None,
                       site: str = "") -> dict:
    """Return legit backlink opportunities for ANY business in ANY country: matching citation/directory/profile
    sites (filtered by niche and country) plus ready-to-run web-search footprint queries (roundups, local lists,
    guest posts, resource pages, podcasts, partners, competitor mentions). Run the queries with web search.
    Pass site= to use a saved project's niche/location/country/keywords/competitors (anything you pass wins).
    niche examples: software, saas, digital marketing, manufacturing, restaurant, salon, gym, hotel, dental clinic,
    law firm, real estate, plumber, interior design, school, online store, wedding photographer, charity.
    country: name or code (India, US, UK, UAE, Australia, Germany...)."""
    pr = _project(site)
    niche = niche or pr.get("niche") or ""
    location = location or pr.get("location") or ""
    code = resolve_country(country) or pr.get("country")
    if country and not resolve_country(country):
        return {"error": f"Unknown country {country!r}. Use a name or ISO code (India/IN, UK/GB, US, UAE/AE...)."}
    keywords = keywords or pr.get("keywords") or ([niche] if niche else [])
    competitors = competitors or pr.get("competitors") or []
    if not niche and not keywords:
        return {"error": "Tell me the niche (e.g. 'dental clinic', 'software', 'restaurant'), or pass site= for a saved project."}
    tags = {"general"} | _niche_tags(niche + " " + " ".join(keywords))
    if location:
        tags.add("local")
    picks = [d for d in _all_directories() if set(d["tags"]) & tags and region_matches(d["region"], code)
             and (not d.get("location") or (location and d["location"].lower() in location.lower()))]
    # rank: priority, +1 when the directory is specific to this niche (not just general/local), niche-specific first on ties
    niche_tags = tags - {"general", "local"}
    for d in picks:
        d["_specific"] = bool(set(d["tags"]) & niche_tags)
    picks.sort(key=lambda d: (-(d["priority"] + d["_specific"]), not d["_specific"], -d["priority"], d["name"]))
    picks = [{k: v for k, v in d.items() if k != "_specific"} | {"why": "niche" if d["_specific"] else "general"} for d in picks]
    cname = country_name(code) if code else ""
    kw = [k for k in keywords if k] or [niche]
    queries = []
    for group, tmpls in _all_footprints().items():
        for t in tmpls:
            if ("{loc}" in t and not location) or ("{country}" in t and not cname):
                continue
            for k in (kw[:3] if "{kw}" in t else kw[:1]):
                q = " ".join(t.format(kw=k, loc=location, country=cname).split())
                queries.append({"type": group, "query": q})
    seen, uniq = set(), []
    for q in queries:
        if q["query"].lower() not in seen:
            seen.add(q["query"].lower())
            uniq.append(q)
    comp = []
    for c in competitors:
        cd = _domain(c)
        comp += [{"type": "competitor_mentions", "query": f'"{cd}" -site:{cd}'},
                 {"type": "competitor_profiles", "query": f'"{cd}" (directory OR listing OR profile OR review)'}]
    notes = []
    if not code:
        notes.append("No country set - only global directories are shown. Pass country= (or save_project) for local ones.")
    if tags == {"general"} or tags == {"general", "local"}:
        notes.append(f"Niche {niche!r} didn't match a known category - showing general directories. "
                     "Try a common word (e.g. 'dentist', 'lawyer', 'software'), or add your own with add_custom_directory.")
    return {
        "used": {"niche": niche, "location": location, "country": cname or None, "keywords": kw,
                 "competitors": competitors, "matched_tags": sorted(tags)},
        "notes": notes,
        "citations_and_directories": picks,
        "search_footprints": uniq[:70] + comp,
        "how_to_use": [
            "Claim high-priority citations first (Google Business Profile, Bing Places, then niche directories).",
            "Use the exact same Name/Address/Phone everywhere (see build_submission_kit).",
            "Run footprint queries with web search (roundups/local lists first - they convert best for local businesses).",
            "qualify_prospect each result with topic_keywords; use its recommended_template in draft_outreach.",
            "'check_manually' verdicts are blocked sites, not bad ones - open them in a browser.",
            "Aim for relevance over volume: 10 relevant links beat 200 junk ones.",
        ],
    }


@mcp.tool()
def add_custom_directory(name: str, url: str, tags: list[str], region: str = "global", priority: int = 3,
                         notes: str = "", location: str = "") -> dict:
    """Add your own directory/citation site so find_opportunities includes it from now on (saved to
    ~/.backlink-mcp/custom.json, survives updates). tags = niches it suits, e.g. ["legal", "local"] (see
    NICHE_TAGS in data.py); region = "global", a country (name or code) or a region (EU, GCC, ANZ, NA, SEA).
    location = optional city/area; if set, it only shows for projects in that location (e.g. a city chamber)."""
    reg = region if region.upper() in ("GLOBAL", "EU", "EUROPE", "GCC", "ANZ", "NA", "SEA", "SOUTH_ASIA") else resolve_country(region)
    if not reg:
        return {"ok": False, "msg": f"Unknown region {region!r}."}
    if not url.startswith("http"):
        return {"ok": False, "msg": "url must start with http(s)://"}
    c = _custom()
    dirs = [d for d in (c.get("directories") or []) if d.get("name", "").lower() != name.lower()]
    entry = {"name": name, "url": url, "tags": [t.lower() for t in tags] or ["general"], "region": reg.lower() if reg.upper() == "GLOBAL" else reg.upper(),
             "priority": max(1, min(5, priority)), "notes": notes}
    if location:
        entry["location"] = location
    dirs.append(entry)
    c["directories"] = dirs
    _save(CUSTOM, c)
    return {"ok": True, "added": entry, "file": str(CUSTOM), "custom_directories": len(dirs)}


@mcp.tool()
def add_custom_footprint(group: str, query: str) -> dict:
    """Add your own search footprint (saved to custom.json). Use {kw} for keyword, {loc} for city/area and
    {country} for the country name, e.g. group "local", query '{loc} {kw} association members'."""
    if not re.search(r"\{(kw|loc|country)\}", query) and len(query.split()) < 2:
        return {"ok": False, "msg": "Query looks too short - use {kw}, {loc} or {country} placeholders."}
    c = _custom()
    fp = c.get("footprints") or {}
    fp.setdefault(group, [])
    if query not in fp[group]:
        fp[group].append(query)
    c["footprints"] = fp
    _save(CUSTOM, c)
    return {"ok": True, "group": group, "queries": fp[group], "file": str(CUSTOM)}


SPAM_LINK_RE = re.compile(r"\b(casino|poker|slot[s-]?|betting|bet365|1xbet|viagra|cialis|payday|escort|porn|"
                          r"xxx|essay[- ]?writing|buy[- ]?followers|crack(ed)?[- ]?software)\b", re.I)
ROUNDUP_RE = re.compile(r"\b(top|best|leading|list of|\d{1,3}\+?)\b.{0,60}\b(companies|agencies|firms|developers|"
                        r"startups|providers|vendors|tools|software|apps|platforms|consultants|manufacturers|suppliers)\b", re.I)
CONTACT_LINK_RE = re.compile(r"contact|about|write[- ]?for[- ]?us|contribute|guest|advertis|submit|editor|team|reach", re.I)


async def _fetch(c: httpx.AsyncClient, url: str):
    try:
        return await c.get(url, headers=BROWSER_HEADERS)
    except Exception as e:  # noqa: BLE001
        return e


@mcp.tool()
async def qualify_prospect(url: str, my_domain: str = "", topic_keywords: list[str] | None = None) -> dict:
    """Fetch a prospect page and score it 0-100. Detects guest-post pages, roundup/"top N companies" lists
    (ask to be included), resource pages and directories; checks noindex, outbound spam links and sponsored-only
    policies; follows the site's contact/about/write-for-us pages to find real contact emails; and says which
    outreach template to use. topic_keywords (e.g. ["dentist", "dental"]) raises the score for relevant pages;
    if omitted, the saved project's keywords for my_domain are used."""
    if not topic_keywords and my_domain:
        pr = _project(my_domain)
        topic_keywords = [w for k in (pr.get("keywords") or []) for w in [k]] + ([pr["niche"]] if pr.get("niche") else [])
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as c:
        r = await _fetch(c, url)
        if isinstance(r, Exception):
            return {"url": url, "ok": False, "error": str(r), "verdict": "check_manually"}
        if r.status_code in (401, 403, 429, 503):
            return {"url": url, "ok": False, "status": r.status_code, "verdict": "check_manually",
                    "note": "Site blocks automated requests. Open it in a browser (or fetch it with web search/fetch) "
                            "and judge it yourself - a block is not a quality signal."}
        if r.status_code >= 400 or "html" not in r.headers.get("content-type", ""):
            return {"url": url, "ok": False, "status": r.status_code, "verdict": "skip"}
        p = _parse_page(str(r.url), r.text)
        dom = _domain(str(r.url))
        low_text = (p["text_sample"] + " " + " ".join(filter(None, [p["title"], *p["h1"], *p["h2"]]))).lower()
        title_h1 = " ".join(filter(None, [p["title"], *p["h1"]]))
        ext = [l for l in p["links"] if _domain(l["href"]) != dom]
        spam_links = [l["href"] for l in ext if SPAM_LINK_RE.search(l["href"] + " " + l["text"])]

        # follow contact-ish pages on the same site to find a real contact
        contact_pages = []
        for l in p["links"]:
            if _domain(l["href"]) == dom and CONTACT_LINK_RE.search(l["href"] + " " + l["text"]) and l["href"] not in contact_pages:
                contact_pages.append(l["href"])
        emails = list(p["emails"])
        write_page = None
        for resp, cu in zip(await asyncio.gather(*(_fetch(c, u) for u in contact_pages[:4])), contact_pages[:4]):
            if isinstance(resp, Exception) or resp.status_code >= 400:
                continue
            cp = _parse_page(str(resp.url), resp.text)
            emails += cp["emails"]
            if re.search(r"write for us|guest post guidelines|submit a guest post|become a contributor", cp["text_sample"], re.I):
                write_page = cu
    emails = _clean_emails(emails)
    emails.sort(key=lambda e: (not e.endswith(dom), not re.match(r"(editor|content|marketing|hello|contact|info|team)@", e)))

    signals = {
        "write_for_us": bool(write_page or re.search(
            r"write for us|guest post(ing)? guidelines|submit a guest post|become a (guest )?contributor|accepting guest posts",
            low_text)),
        "roundup_list": bool(ROUNDUP_RE.search(title_h1)),
        "resource_page": bool(re.search(r"\b(useful links|recommended (tools|resources|sites)|resources? (page|list)|tools we (use|love))\b", low_text)
                              or re.search(r"\bresources?\b", title_h1, re.I)),
        "directory": bool(re.search(r"add (your )?(listing|business|company|site)|submit (your )?(site|listing|business|company)|list your (business|company)|claim (your )?(profile|listing)", low_text)),
        "sponsored_only": bool(re.search(r"sponsored posts? only|paid (guest )?posts? only|guest post price|price for (a )?guest post", low_text)),
        "noindex": bool(p["robots"] and "noindex" in p["robots"].lower()),
        "spam_outbound_links": len(spam_links) >= 2,
    }
    kws = [k.lower() for k in (topic_keywords or [])]
    relevant = bool(kws) and any(k in low_text for k in kws)
    already = [l for l in p["links"] if my_domain and _domain(l["href"]) == _domain(my_domain)]

    score = 40
    score += 25 * signals["write_for_us"] + 20 * signals["roundup_list"] + 10 * signals["resource_page"]
    score += 15 * signals["directory"] + (10 if emails else 0) + (10 if relevant else 0)
    score += 5 if p["word_count"] > 800 else 0
    score -= 40 * signals["noindex"] + 60 * signals["spam_outbound_links"] + 15 * signals["sponsored_only"]
    score -= 15 if len(ext) > 200 else 0
    if kws and not relevant:
        score -= 15
    score = max(0, min(100, score))

    if already:
        approach = ("already_linked", "They already link to you - check anchor/rel with verify_backlink; no outreach needed.")
    elif signals["directory"]:
        approach = ("signup", "Create/claim a profile on the site - no email needed.")
    elif signals["write_for_us"]:
        approach = ("guest_post", f"Pitch an article{' via ' + write_page if write_page else ''}.")
    elif signals["roundup_list"]:
        approach = ("list_inclusion", "Ask to be considered for this list - send real proof (projects, clients, reviews).")
    elif signals["resource_page"]:
        approach = ("resource_page", "Suggest one genuinely useful page of yours for their list.")
    else:
        approach = ("skip_or_manual", "No clear link opportunity on this page.")

    return {
        "url": str(r.url), "ok": True, "title": p["title"], "lang": p["lang"], "signals": signals,
        "relevant_to_topic": relevant if kws else None, "outbound_links": len(ext), "spam_link_examples": spam_links[:3],
        "word_count": p["word_count"], "contact_emails": emails[:5],
        "contact_pages_checked": contact_pages[:4], "write_for_us_page": write_page,
        "already_links_to_you": already, "score_0_100": score,
        "verdict": "skip" if score < 40 else ("good" if score >= 65 else "maybe"),
        "recommended_template": approach[0], "how_to_approach": approach[1],
        "next": "If good: tracker_add, then draft_outreach with recommended_template (unless signup/already_linked).",
    }


_DANGLING = {"a", "an", "the", "and", "or", "for", "of", "to", "in", "with", "on", "at", "by", "from", "our", "your"}
ACRONYMS = {"erp", "crm", "hrms", "hr", "it", "ai", "ml", "seo", "ui", "ux", "api", "saas", "b2b", "iot", "plc", "amc",
            "pos", "cms", "lms", "gst", "mis", "ios", "qa", "msme"}


def _cut(text: str, n: int) -> str:
    """Trim to n chars at a word boundary; prefer ending at a sentence; never leave a dangling 'for/and/the'."""
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    head = text[:n]
    end = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    if end >= n * 0.5:
        return head[: end + 1]
    words = head.rsplit(" ", 1)[0].rstrip(",;:-–— ").split()
    while words and words[-1].lower() in _DANGLING:
        words.pop()
    return " ".join(words).rstrip(",;:-–— ")


def _smart_title(phrase: str) -> str:
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in phrase.split())


def _guess_category(profile: dict, extra_text: str = "") -> str | None:
    txt = " ".join([*(profile.get("keywords") or []), profile.get("description") or "", extra_text]).lower()
    for keys, cat in _all_category_hints():
        if any(k in txt for k in keys):
            return cat
    return None


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else (", ".join(items[:-1]) + " and " + items[-1] if items else "")


@mcp.tool()
def build_submission_kit(domain: str, business_name: str = "", category: str = "", phone: str = "",
                         email: str = "", address: str = "", city: str = "", state: str = "",
                         postal_code: str = "", country: str = "", founded: str = "",
                         services: list[str] | None = None, socials: list[str] | None = None,
                         description: str = "", save: bool = True) -> dict:
    """Build one consistent Name/Address/Phone + descriptions kit for directory/citation sign-ups. Merges the
    cached scan profile with fields you pass (yours win). Placeholder values (XXXX, 20XX, "your address"...) are
    rejected, never saved. Returns needs_review so you know what to fix before submitting. Saves .md + .json;
    generate_schema reuses it."""
    d = _load(CACHE / f"{_domain(domain)}.json", {}) or {}
    pr = d.get("profile", {}) or {}
    proj = _project(domain)
    a = pr.get("address") or {}
    rejected = {}
    if country and not resolve_country(country):
        rejected["country"] = country
        country = ""

    def pick(field: str, given, fallback=None):
        if isinstance(given, list):
            good = [g for g in given if not _is_placeholder(g)]
            if len(good) != len(given):
                rejected[field] = [g for g in given if _is_placeholder(g)]
            return good or fallback
        if given and _is_placeholder(given):
            rejected[field] = given
            given = None
        if fallback and _is_placeholder(fallback):
            fallback = None
        return given or fallback

    name = pick("business_name", business_name, proj.get("name") or pr.get("name"))
    brand = _brand_words(name, _domain(domain))
    svc_default = []
    for k in (pr.get("keywords") or []):
        words = k.split()
        # real service phrases only: 2+ words, not brand, not two acronyms glued together ("erp crm"), no overlap
        if len(words) < 2 or set(words) & brand or all(w in ACRONYMS for w in words):
            continue
        if any(k in s_.lower() or s_.lower() in k for s_ in svc_default):
            continue
        svc_default.append(_smart_title(k))
    svc_default = svc_default[:5]
    kit = {
        "business_name": name,
        "website": pr.get("website") or f"https://{_domain(domain)}",
        "category": pick("category", category, _guess_category(pr, " ".join([*(services or []), proj.get("niche") or ""]))),
        "phone": pick("phone", phone, pr.get("phone")),
        "email": pick("email", email, pr.get("email")),
        "street_address": pick("address", address, a.get("streetAddress")),
        "city": pick("city", city, a.get("addressLocality") or proj.get("location")),
        "state": pick("state", state, a.get("addressRegion")),
        "postal_code": pick("postal_code", postal_code, a.get("postalCode")),
        "country": country_name(pick("country", country, a.get("addressCountry") or proj.get("country"))) or None,
        "founded": pick("founded", founded),
        "services": pick("services", services, svc_default),
        "social_profiles": pick("socials", socials, pr.get("same_as") or []),
        "logo": pr.get("logo"),
    }
    if kit["category"] and set(kit["category"].lower().split()) <= brand:
        rejected["category"] = kit["category"]
        kit["category"] = _guess_category(pr)
    if kit["phone"]:
        # one display format used everywhere + E.164 for schema; works for any country
        kit["phone"], kit["phone_e164"] = format_phone(kit["phone"], kit["country"])

    base = pick("description", description, pr.get("description")) or ""
    svc = kit["services"] or []
    where = f" in {kit['city']}" if kit["city"] else ""
    cat = (kit["category"] or "company").lower()
    intro = f"{kit['business_name']} is a {cat}{where}" + (f" offering {_join(svc[:4])}." if svc else ".")
    long_parts = [base or intro]
    if base:  # description already introduces the business; add the concrete details after it
        city_known = bool(kit["city"]) and kit["city"].lower() in base.lower()
        if svc:
            long_parts.append((f"Based{where}, we offer " if where and not city_known else "We offer ") + _join(svc[:4]) + ".")
        elif where and not city_known:
            long_parts.append(f"We are based{where}.")
    if kit["founded"]:
        long_parts.append(f"Founded in {kit['founded']}" + (f", we serve clients across {country_name(kit['country'], article=True)}." if kit["country"] else "."))
    if len(svc) > 4:
        long_parts.append(f"We also offer {_join(svc[4:7])}.")
    kit["descriptions"] = {
        "tagline_60": _cut(base or f"{kit['category'] or 'Business'}{where}", 60),
        "short_160": _cut(base or intro, 160),
        "long_750": _cut(" ".join(x for x in long_parts if x), 750),
    }
    required = {"business_name": "Business name", "category": "Category", "phone": "Phone", "email": "Email",
                "street_address": "Street address", "city": "City", "postal_code": "Postal / ZIP / PIN code",
                "country": "Country"}
    missing = [label for k, label in required.items() if not kit.get(k)]
    needs_review = []
    if missing:
        needs_review.append(f"Missing: {', '.join(missing)}.")
    if not kit["street_address"]:
        needs_review.append("No street address - Google Business Profile and most local directories need one. "
                            "Use your registered office address and show the same address on your website's contact page.")
    if rejected:
        needs_review.append(f"Ignored placeholder values: {rejected} - pass your real details.")
    if not base:
        needs_review.append("No site description found - pass description= with 1-2 sentences in your own words.")
    needs_review.append("Read the descriptions once and adjust wording to sound like you.")
    kit.update({"missing_fields": missing, "rejected_placeholders": rejected, "needs_review": needs_review,
                "ready_to_submit": not missing and not rejected})
    kit["rules"] = ["Copy name, address and phone EXACTLY as written here on every site - same spelling, same format.",
                    "Link to your homepage unless the directory is about one specific product/service page.",
                    "Use the same logo and the closest primary category everywhere."]
    if save:
        out_json = DATA_DIR / f"submission_kit_{_domain(domain)}.json"
        out_md = DATA_DIR / f"submission_kit_{_domain(domain)}.md"
        _save(out_json, kit)
        addr_line = ", ".join(x for x in (kit["street_address"], kit["city"], kit["state"], kit["postal_code"], kit["country"]) if x)
        md = [f"# Submission kit: {kit['business_name']}", "",
              "**Status:** " + ("ready to submit" if kit["ready_to_submit"] else "needs review (see bottom)"), "",
              "## Copy-paste details", "", "| Field | Value |", "|---|---|"]
        rows = [("Business name", kit["business_name"]), ("Website", kit["website"]), ("Category", kit["category"]),
                ("Phone", kit["phone"]), ("Email", kit["email"]), ("Address", addr_line), ("Founded", kit["founded"]),
                ("Services", ", ".join(svc)), ("Social profiles", ", ".join(kit["social_profiles"])), ("Logo", kit["logo"])]
        md += [f"| {k} | {v or '_missing_'} |" for k, v in rows]
        md += ["", "## Descriptions", ""]
        md += [f"**Tagline (≤60):** {kit['descriptions']['tagline_60']}", "",
               f"**Short (≤160):** {kit['descriptions']['short_160']}", "",
               f"**Long (≤750):** {kit['descriptions']['long_750']}", "", "## Rules", ""]
        md += [f"- {r}" for r in kit["rules"]]
        md += ["", "## Needs review", ""] + [f"- {r}" for r in needs_review]
        out_md.write_text("\n".join(md), "utf-8")
        kit["saved_to"] = [str(out_json), str(out_md)]
    return kit


@mcp.tool()
def generate_schema(domain: str, business_type: str = "ProfessionalService", area_served: str = "",
                    price_range: str = "") -> dict:
    """Generate ready-to-paste LocalBusiness JSON-LD (name, address, phone, email, logo, sameAs, foundingDate)
    from the saved submission kit (or the last scan). Paste the returned script tag into your site's <head>
    (e.g. index.html). business_type: ProfessionalService, LocalBusiness, Organization, Restaurant,
    BeautySalon, Hotel, MedicalClinic, Store... Fields still missing are listed, never invented."""
    dom = _domain(domain)
    kit = _load(DATA_DIR / f"submission_kit_{dom}.json", None)
    if not kit:
        pr = (_load(CACHE / f"{dom}.json", {}) or {}).get("profile", {})
        a = pr.get("address") or {}
        kit = {"business_name": pr.get("name"), "website": pr.get("website") or f"https://{dom}",
               "phone": pr.get("phone"), "email": pr.get("email"), "street_address": a.get("streetAddress"),
               "city": a.get("addressLocality"), "state": a.get("addressRegion"), "postal_code": a.get("postalCode"),
               "country": a.get("addressCountry"), "social_profiles": pr.get("same_as") or [], "logo": pr.get("logo"),
               "descriptions": {"short_160": pr.get("description")}}
    if not kit.get("business_name"):
        return {"error": "No business details yet. Run scan_site or build_submission_kit first."}
    site = kit.get("website") or f"https://{dom}"
    schema: dict[str, Any] = {"@context": "https://schema.org", "@type": business_type,
                              "@id": site.rstrip("/") + "/#business", "name": kit["business_name"], "url": site}
    desc = (kit.get("descriptions") or {}).get("short_160")
    for k, v in (("description", desc), ("telephone", kit.get("phone_e164") or kit.get("phone")),
                 ("email", kit.get("email")), ("logo", kit.get("logo")), ("image", kit.get("logo")),
                 ("foundingDate", kit.get("founded")), ("priceRange", price_range or None)):
        if v and not _is_placeholder(v):
            schema[k] = v
    addr = {k: v for k, v in (("streetAddress", kit.get("street_address")), ("addressLocality", kit.get("city")),
                              ("addressRegion", kit.get("state")), ("postalCode", kit.get("postal_code")),
                              ("addressCountry", resolve_country(kit.get("country")) or kit.get("country")))
            if v and not _is_placeholder(v)}
    if addr:
        schema["address"] = {"@type": "PostalAddress", **addr}
    if area_served or kit.get("city"):
        schema["areaServed"] = area_served or kit.get("country") or kit.get("city")
    if kit.get("social_profiles"):
        schema["sameAs"] = kit["social_profiles"]
    street_label = ("street address (required by Google for LocalBusiness results)"
                    if business_type not in ("Organization", "Corporation") else "street address")
    missing = [f for f, ok in ((street_label, "streetAddress" in addr), ("postal code", "postalCode" in addr),
                               ("phone", "telephone" in schema), ("logo", "logo" in schema),
                               ("sameAs social links", "sameAs" in schema)) if not ok]
    tag = '<script type="application/ld+json">\n' + json.dumps(schema, indent=2, ensure_ascii=False) + "\n</script>"
    return {"script_tag": tag, "missing": missing,
            "where_to_paste": "Inside <head> of index.html (Vite/static), app/layout.tsx via <script> (Next.js), "
                              "or base.html (Django). Use it once site-wide, not on every component.",
            "validate_at": "https://validator.schema.org/ and https://search.google.com/test/rich-results"}


@mcp.tool()
def draft_outreach(template: str, my_site: str, my_name: str, target_site: str = "",
                   contact_name: str = "", topic: str = "", my_page: str = "", broken_url: str = "",
                   proof: list[str] | None = None, hook: str = "", extra: str = "") -> dict:
    """Draft an outreach email to edit and send yourself (never sends anything).
    template: guest_post | list_inclusion (for "top N companies" roundups) | resource_page | broken_link |
    unlinked_mention | partner | testimonial | local_press.
    topic: a noun phrase, e.g. "how to choose a family dentist" or "local bakery wins state award".
    proof: real facts only, e.g. ["Served 200+ local families since 2019", "4.9 stars from 120 Google reviews"].
    hook: ONE specific sentence about their page so it doesn't read as a mass email.
    Returns warnings when something required is missing - fix them before sending."""
    templates = _all_templates()
    t = templates.get(template)
    if not t:
        return {"error": f"Unknown template. Use one of: {', '.join(templates)}"}
    given = {"topic": topic, "my_page": my_page, "broken_url": broken_url, "proof": proof}
    warnings = [f"'{k}' is needed for {template} - pass it (see the tool description)." for k in t.get("needs", []) if not given.get(k)]
    for k, v in {"topic": topic, "contact_name": contact_name, "target_site": target_site, "hook": hook,
                 "my_page": my_page}.items():
        if v and _is_placeholder(v):
            warnings.append(f"'{k}' looks like a placeholder ({v!r}).")
    if topic and re.match(r"(?i)(top|best)\b", topic) and template == "local_press":
        warnings.append("topic reads like a list title, not news - use something like 'local firm launches X'.")
    if not hook:
        warnings.append("No hook: add one sentence about their specific page, otherwise it reads like spam.")
    if not contact_name:
        warnings.append("No contact name - try the site's About/Team page; 'Hi there' gets fewer replies.")
    proof_txt = ("\n".join(f"- {x}" for x in (proof or []) if x and not _is_placeholder(x)) + "\n") if proof else ""
    vals = {"my_site": my_site, "my_name": my_name, "target_site": target_site or "your site",
            "contact": contact_name or "there", "topic": topic or "[topic]",
            "my_page": my_page or my_site, "broken_url": broken_url or "[broken link]",
            "proof": proof_txt, "hook": hook or "[One sentence about their specific page.]"}
    body = t["body"].format(**vals).strip()
    if extra:
        body = body.replace(f"\n{my_name}", f"\n{extra.strip()}\n\n{my_name}", 1)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return {"subject": t["subject"].format(**vals), "body": body, "warnings": warnings,
            "ready_to_send": not warnings,
            "tips": ["Send from your domain email (not Gmail), under 150 words.",
                     "Follow up once after 5-7 days, then stop."]}


# ----------------------------------------------------------------- tools: verification & tracking
@mcp.tool()
async def verify_backlink(source_url: str, target_domain: str) -> dict:
    """Check whether a page links to your domain: anchor text, rel (nofollow/sponsored/ugc), target URL,
    and whether the source page is indexable. Updates any matching tracker entry."""
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as c:
        try:
            r = await c.get(source_url)
        except Exception as e:
            return {"source": source_url, "live": False, "error": str(e)}
    soup = BeautifulSoup(r.text, "lxml")
    td = _domain(target_domain)
    found = [{"href": a["href"], "anchor": " ".join(a.get_text(" ").split())[:100],
              "rel": " ".join(a.get("rel", [])) or "follow"}
             for a in soup.find_all("a", href=True) if _domain(urljoin(str(r.url), a["href"])) == td]
    robots = (soup.find("meta", attrs={"name": "robots"}) or {}).get("content", "") or ""
    res = {"source": str(r.url), "status": r.status_code, "live": bool(found), "links": found,
           "source_noindex": "noindex" in robots.lower() or "noindex" in r.headers.get("x-robots-tag", ""),
           "checked_at": _now()}
    tr = _load(TRACKER, [])
    for e in tr:
        if _norm(e.get("url", "")) == _norm(source_url):
            e["last_check"] = res["checked_at"]
            e["link_live"] = res["live"]
            if res["live"] and e.get("status") not in ("live",):
                e["status"] = "live"
    _save(TRACKER, tr)
    return res


@mcp.tool()
def tracker_add(url: str, kind: str, site: str, notes: str = "", contact: str = "",
                status: str = "todo") -> dict:
    """Add a backlink opportunity to the tracker. kind: citation | directory | guest_post | resource_page |
    broken_link | mention | partner | press | profile. status: todo | submitted | pitched | live | rejected."""
    tr = _load(TRACKER, [])
    if any(_norm(e["url"]) == _norm(url) and _domain(e["site"]) == _domain(site) for e in tr):
        return {"ok": False, "msg": "Already tracked."}
    same_site = [e for e in tr if _domain(e["url"]) == _domain(url) and _domain(e["site"]) == _domain(site)]
    if same_site and kind in ("directory", "citation", "profile"):
        return {"ok": False, "msg": f"{_domain(url)} is already tracked as #{same_site[0]['id']} - one profile per "
                                    "directory is enough. Use tracker_update to add a note instead."}
    e = {"id": (max([x["id"] for x in tr], default=0) + 1), "url": url, "kind": kind, "site": _domain(site),
         "status": status, "contact": contact, "notes": notes, "added": _now(), "updated": _now()}
    tr.append(e)
    _save(TRACKER, tr)
    res = {"ok": True, "entry": e}
    if same_site:
        res["warning"] = f"Same site already tracked as #{same_site[0]['id']} - make sure this is a separate opportunity."
    return res


@mcp.tool()
def tracker_update(id: int, status: str = "", notes: str = "", contact: str = "") -> dict:
    """Update a tracker entry's status/notes/contact by id."""
    tr = _load(TRACKER, [])
    for e in tr:
        if e["id"] == id:
            if status:
                e["status"] = status
            if notes:
                e["notes"] = (e.get("notes", "") + " | " + notes).strip(" |")
            if contact:
                e["contact"] = contact
            e["updated"] = _now()
            _save(TRACKER, tr)
            return {"ok": True, "entry": e}
    return {"ok": False, "msg": f"No entry {id}"}


@mcp.tool()
def tracker_list(site: str = "", status: str = "") -> dict:
    """List tracked opportunities, optionally filtered by your site and/or status, with a summary."""
    tr = [e for e in _load(TRACKER, []) if (not site or e["site"] == _domain(site))
          and (not status or e["status"] == status)]
    return {"summary": dict(Counter(e["status"] for e in tr)), "count": len(tr), "entries": tr,
            "file": str(TRACKER)}


@mcp.tool()
async def recheck_live_links(site: str) -> dict:
    """Re-verify every 'live' tracker entry for a site and flag links that disappeared or became nofollow."""
    tr = [e for e in _load(TRACKER, []) if e["site"] == _domain(site) and e["status"] == "live"]
    results = await asyncio.gather(*(verify_backlink(e["url"], site) for e in tr))
    lost = [r["source"] for r in results if not r["live"]]
    return {"checked": len(results), "lost": lost,
            "nofollow": [r["source"] for r in results if r["live"] and all("nofollow" in l["rel"] for l in r["links"])]}


def _serve_http(port: int, host: str) -> None:
    """Streamable-HTTP mode for claude.ai custom connectors (run behind an HTTPS tunnel).
    The endpoint lives under a secret path, so only someone with the full URL can use it."""
    import secrets
    import uvicorn

    token_file = DATA_DIR / "http_token"
    token = os.environ.get("BACKLINK_MCP_TOKEN") or (token_file.read_text().strip() if token_file.exists() else "")
    if not token:
        token = secrets.token_urlsafe(24)
        token_file.write_text(token)
        token_file.chmod(0o600)
    path = f"/{token}/mcp"
    try:  # mcp >= 2.0
        from mcp.server.transport_security import TransportSecuritySettings
        app = mcp.streamable_http_app(
            streamable_http_path=path,
            # Tunnels send their public Host header; the secret path is the access control instead.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
            host=host,
        )
    except TypeError:  # mcp 1.x
        mcp.settings.streamable_http_path = path
        if hasattr(mcp.settings, "transport_security"):
            from mcp.server.transport_security import TransportSecuritySettings
            mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
        app = mcp.streamable_http_app()
    import sys
    print(f"\nbacklink-mcp HTTP running on http://{host}:{port}{path}", file=sys.stderr)
    print("Expose it:   cloudflared tunnel --url http://localhost:%d" % port, file=sys.stderr)
    print(f"claude.ai connector URL:  https://<your-tunnel-host>{path}\n", file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="backlink-mcp")
    ap.add_argument("--http", action="store_true", help="serve over HTTP for claude.ai custom connectors")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--new-token", action="store_true", help="rotate the secret URL token")
    a = ap.parse_args()
    if a.new_token:
        (DATA_DIR / "http_token").unlink(missing_ok=True)
    if a.http:
        _serve_http(a.port, a.host)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
