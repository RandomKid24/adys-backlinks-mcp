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

from .data import DIRECTORIES, FOOTPRINTS, OUTREACH_TEMPLATES

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
                   "Accept-Language": "en-IN,en;q=0.9"}


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
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        links.append({"href": _norm(urljoin(url, href)), "text": " ".join(a.get_text(" ").split())[:80],
                      "rel": " ".join(a.get("rel", []))})
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
        "next": "Run seo_link_audit, then find_opportunities.",
    }


@mcp.tool()
def scan_codebase(path: str, max_files: int = 3000) -> dict:
    """Scan a local website project (React/Vite, Next.js, Django, plain HTML, etc.): detect framework,
    routes/pages, meta tags, sitemap/robots, structured data, contact details and external links.
    Use when the site isn't live yet or to find what to fix in code."""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"error": f"Not a directory: {root}"}
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


@mcp.tool()
def internal_link_suggestions(domain: str, limit: int = 20) -> list[dict]:
    """Suggest internal links (source page -> target page, anchor text) for weakly-linked pages, based on
    keyword overlap from the cached scan. Internal linking passes backlink equity to deeper pages."""
    d = _load(CACHE / f"{_domain(domain)}.json", None)
    if not d:
        return [{"error": "No scan cached. Run scan_site first."}]
    pages, dom = d["pages"], d["domain"]
    inbound = Counter(l["href"] for p in pages.values() for l in p["links"] if _domain(l["href"]) == dom)
    brand = set(re.findall(r"[a-z]+", (d.get("profile", {}).get("name") or "").lower()))
    title_words = Counter(w for p in pages.values() for w in set(re.findall(r"[a-z]+", (p["title"] or "").lower())))
    common = {w for w, c in title_words.items() if c > len(pages) * 0.6} if len(pages) >= 5 else set()
    brand |= _brand_words(None, dom)
    out = []
    for tu, tp in sorted(pages.items(), key=lambda kv: inbound[kv[0]]):
        if len(out) >= limit:
            break
        src_text = " ".join(filter(None, [tp["title"], *tp["h1"], *tp.get("h2", [])[:3], tp["meta_description"]]))
        kws = [k for k in _keywords(src_text, 12, brand | common) if len(k) > 3]
        # multi-word phrases make better, more descriptive anchors - try them first
        kws = sorted(kws, key=lambda k: -len(k.split()))[:6]
        linked_from = {su for su, sp in pages.items() if any(l["href"] == tu for l in sp["links"])}
        picks = 0
        for su, sp in sorted(pages.items(), key=lambda kv: -inbound[kv[0]]):  # strongest pages first
            if su == tu or su in linked_from or picks >= 3:
                continue
            txt = sp["text_sample"].lower()
            hit = next((k for k in kws if re.search(rf"\b{re.escape(k)}\b", txt)), None)
            if hit:
                out.append({"from": su, "to": tu, "anchor": hit, "target_inbound_now": inbound[tu],
                            "source_strength": inbound[su]})
                picks += 1
    return out[:limit]


# ----------------------------------------------------------------- tools: opportunities
@mcp.tool()
def find_opportunities(niche: str, location: str = "", country: str = "IN",
                       keywords: list[str] | None = None, competitors: list[str] | None = None) -> dict:
    """Return legit backlink opportunities for a business: matching citation/directory/profile sites
    (filtered by niche & country) plus ready-to-run web-search footprint queries for guest posts,
    resource pages, local news, partners and unlinked mentions. Run the queries with web search.
    niche examples: software, it-services, saas, manufacturing, restaurant, salon, hotel, healthcare, education."""
    n = niche.lower()
    tagmap = {"software": ["software", "it", "saas", "agency"], "it": ["it", "software", "agency"],
              "saas": ["saas", "software"], "erp": ["software", "saas", "it"], "web": ["agency", "it", "design"],
              "manufactur": ["manufacturing", "b2b"], "industrial": ["manufacturing", "b2b"], "pharma": ["manufacturing", "b2b"],
              "restaurant": ["food", "local"], "cafe": ["food", "local"], "salon": ["beauty", "local"],
              "spa": ["beauty", "local"], "hotel": ["hospitality", "local"], "resort": ["hospitality", "local"],
              "clinic": ["healthcare", "local"], "doctor": ["healthcare", "local"], "school": ["education", "local"],
              "design": ["design", "agency"], "startup": ["startup"]}
    tags = {"general"} | {t for k, ts in tagmap.items() if k in n for t in ts}
    if location:
        tags.add("local")
    picks = [d for d in DIRECTORIES
             if (set(d["tags"]) & tags) and (d["region"] in ("global", country.upper()))]
    picks.sort(key=lambda d: (-d["priority"], d["name"]))
    kw = keywords or [niche]
    loc = location or ""
    queries = []
    for group, tmpls in FOOTPRINTS.items():
        for t in tmpls:
            if "{loc}" in t and not loc:
                continue
            for k in (kw[:3] if "{kw}" in t else kw[:1]):
                queries.append({"type": group, "query": t.format(kw=k, loc=loc).strip()})
    seen, uniq = set(), []
    for q in queries:
        if q["query"] not in seen:
            seen.add(q["query"])
            uniq.append(q)
    comp = []
    for c in competitors or []:
        cd = _domain(c)
        comp += [{"type": "competitor_mentions", "query": f'"{cd}" -site:{cd}'},
                 {"type": "competitor_profiles", "query": f'"{cd}" (directory OR listing OR profile OR review)'}]
    return {
        "citations_and_directories": picks,
        "search_footprints": uniq[:60] + comp,
        "how_to_use": [
            "Claim high-priority citations first (Google Business Profile, Bing Places, then niche directories).",
            "Use the exact same Name/Address/Phone everywhere (see build_submission_kit).",
            "Run footprint queries with web search (roundups/local lists first - they convert best for local businesses).",
            "qualify_prospect each result with topic_keywords; use its recommended_template in draft_outreach.",
            "'check_manually' verdicts are blocked sites, not bad ones - open them in a browser.",
            "Aim for relevance over volume: 10 relevant links beat 200 junk ones.",
        ],
    }


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
    outreach template to use. topic_keywords (e.g. ["erp", "software"]) raises the score for relevant pages."""
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


CATEGORY_HINTS = [  # (keyword in site text, directory-style category)
    (("erp", "crm", "hrms", "saas", "software development", "custom software", "web development", "app development"),
     "Software Company"),
    (("it services", "it company", "it solutions"), "IT Services"),
    (("digital marketing", "seo agency", "social media marketing"), "Digital Marketing Agency"),
    (("web design", "ui design", "ux design", "branding"), "Web Design Agency"),
    (("manufactur", "machining", "fabrication", "industrial equipment", "autoclave", "pharma machinery"), "Manufacturer"),
    (("restaurant", "cafe", "dining", "biryani"), "Restaurant"),
    (("salon", "spa", "beauty", "hair"), "Beauty Salon"),
    (("resort", "farm stay", "hotel", "homestay"), "Resort"),
    (("clinic", "hospital", "dental", "doctor"), "Medical Clinic"),
    (("school", "academy", "coaching", "institute", "training"), "Educational Institution"),
]


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
    for keys, cat in CATEGORY_HINTS:
        if any(k in txt for k in keys):
            return cat
    return None


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else (", ".join(items[:-1]) + " and " + items[-1] if items else "")


@mcp.tool()
def build_submission_kit(domain: str, business_name: str = "", category: str = "", phone: str = "",
                         email: str = "", address: str = "", city: str = "", state: str = "",
                         postal_code: str = "", country: str = "India", founded: str = "",
                         services: list[str] | None = None, socials: list[str] | None = None,
                         description: str = "", save: bool = True) -> dict:
    """Build one consistent Name/Address/Phone + descriptions kit for directory/citation sign-ups. Merges the
    cached scan profile with fields you pass (yours win). Placeholder values (XXXX, 20XX, "your address"...) are
    rejected, never saved. Returns needs_review so you know what to fix before submitting. Saves .md + .json;
    generate_schema reuses it."""
    d = _load(CACHE / f"{_domain(domain)}.json", {}) or {}
    pr = d.get("profile", {}) or {}
    a = pr.get("address") or {}
    rejected = {}

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

    name = pick("business_name", business_name, pr.get("name"))
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
        "category": pick("category", category, _guess_category(pr, " ".join(services or []))),
        "phone": pick("phone", phone, pr.get("phone")),
        "email": pick("email", email, pr.get("email")),
        "street_address": pick("address", address, a.get("streetAddress")),
        "city": pick("city", city, a.get("addressLocality")),
        "state": pick("state", state, a.get("addressRegion")),
        "postal_code": pick("postal_code", postal_code, a.get("postalCode")),
        "country": pick("country", country, a.get("addressCountry")),
        "founded": pick("founded", founded),
        "services": pick("services", services, svc_default),
        "social_profiles": pick("socials", socials, pr.get("same_as") or []),
        "logo": pr.get("logo"),
    }
    if kit["category"] and set(kit["category"].lower().split()) <= brand:
        rejected["category"] = kit["category"]
        kit["category"] = _guess_category(pr)
    digits = re.sub(r"\D", "", kit["phone"] or "")
    if kit["phone"]:
        if len(digits) == 10 and (kit["country"] or "").lower() in ("india", "in"):
            digits = "91" + digits
        kit["phone_e164"] = "+" + digits
        if digits.startswith("91") and len(digits) == 12:
            kit["phone"] = f"+91 {digits[2:7]} {digits[7:]}"  # one display format, used everywhere

    base = pick("description", description, pr.get("description")) or ""
    svc = kit["services"] or []
    where = f" in {kit['city']}" if kit["city"] else ""
    cat = (kit["category"] or "company").lower()
    intro = f"{kit['business_name']} is a {cat}{where}" + (f" that builds {_join(svc[:4])}." if svc else ".")
    long_parts = [base or intro]
    if base:  # description already introduces the business; add the concrete details after it
        long_parts.append((f"Based{where}, we build " if where else "We build ") + _join(svc[:4]) + "." if svc else
                          (f"We are based{where}." if where else ""))
    if kit["founded"]:
        long_parts.append(f"Founded in {kit['founded']}, we work with businesses across {kit['country'] or 'India'}.")
    if len(svc) > 4:
        long_parts.append(f"We also offer {_join(svc[4:7])}.")
    kit["descriptions"] = {
        "tagline_60": _cut(base or f"{kit['category'] or 'Business'}{where}", 60),
        "short_160": _cut(base or intro, 160),
        "long_750": _cut(" ".join(x for x in long_parts if x), 750),
    }
    required = {"business_name": "Business name", "category": "Category", "phone": "Phone", "email": "Email",
                "street_address": "Street address", "city": "City", "postal_code": "PIN / postal code"}
    missing = [label for k, label in required.items() if not kit.get(k)]
    needs_review = []
    if missing:
        needs_review.append(f"Missing: {', '.join(missing)}.")
    if not kit["street_address"]:
        needs_review.append("No street address - Google Business Profile, Justdial and most citations need one. "
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
                              ("addressCountry", "IN" if (kit.get("country") or "").lower() in ("india", "in") else kit.get("country")))
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
    topic: a noun phrase, e.g. "choosing an ERP for a small factory" or "Nashik startup opens AI lab".
    proof: real facts only, e.g. ["Built ERP for 3 Nashik manufacturers", "Founded 2025"].
    hook: ONE specific sentence about their page so it doesn't read as a mass email.
    Returns warnings when something required is missing - fix them before sending."""
    t = OUTREACH_TEMPLATES.get(template)
    if not t:
        return {"error": f"Unknown template. Use one of: {', '.join(OUTREACH_TEMPLATES)}"}
    given = {"topic": topic, "my_page": my_page, "broken_url": broken_url, "proof": proof}
    warnings = [f"'{k}' is needed for {template} - pass it (see the tool description)." for k in t["needs"] if not given.get(k)]
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
