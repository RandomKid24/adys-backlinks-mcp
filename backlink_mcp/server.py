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
        "Workflow: scan_site and/or scan_codebase -> seo_link_audit -> find_opportunities -> "
        "build_submission_kit -> draft_outreach -> tracker_add / tracker_update -> verify_backlink. "
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


def _keywords(text: str, n: int = 15) -> list[str]:
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower()) if w not in STOP]
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
        "emails": sorted(set(EMAIL_RE.findall(html)))[:5],
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
        ext = sorted({l["href"] for p in pages.values() for l in p["links"] if _domain(l["href"]) != dom})[:40]
        res = await asyncio.gather(*(c.head(u) for u in ext), return_exceptions=True)
        broken_out = [{"url": u, "status": getattr(r, "status_code", type(r).__name__)}
                      for u, r in zip(ext, res) if isinstance(r, Exception) or r.status_code >= 400]
    return {"domain": dom, "start": start, "pages": pages, "broken_internal": broken,
            "broken_outbound": broken_out, "robots_txt": robots_txt,
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
    return {
        "name": org.get("name") or (home.get("og") or {}).get("site_name") or (home.get("title") or domain).split("|")[0].split("-")[0].strip(),
        "website": f"https://{domain}",
        "description": org.get("description") or home.get("meta_description"),
        "email": org.get("email") or (emails.most_common(1)[0][0] if emails else None),
        "phone": org.get("telephone") or (phones.most_common(1)[0][0] if phones else None),
        "address": {k: addr.get(k) for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")} if addr else None,
        "logo": org.get("logo") if isinstance(org.get("logo"), str) else (org.get("logo") or {}).get("url"),
        "same_as": org.get("sameAs", []),
        "keywords": _keywords(all_text, 20),
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

    routes, titles, descs, ext_links, emails, phones = set(), set(), set(), Counter(), set(), set()
    files_with_jsonld, files_with_meta, sitemap, robots, text_blob, n = [], [], [], [], "", 0
    for f in root.rglob("*"):
        if n >= max_files:
            break
        if any(part in SKIP_DIRS for part in f.parts) or not f.is_file() or f.suffix.lower() not in CODE_EXT:
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
        routes.update(re.findall(r"""path\s*[:=]\s*["'](/[^"']*)["']""", src))  # react-router
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
            if not re.search(r"(schema\.org|w3\.org|googleapis|gstatic|cdn|unpkg|jsdelivr|npmjs|localhost|127\.0\.0\.1|example\.com|github\.com/[^/]+/[^/]+/(blob|issues))", u):
                ext_links[_domain(u)] += 1
        emails.update(e for e in EMAIL_RE.findall(src) if not re.search(r"(example|\.png|\.jpg|@\d|sentry|noreply)", e))
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
    return {
        "root": str(root), "files_scanned": n, "framework": framework or ["unknown/static"],
        "routes": sorted(routes)[:200], "titles": sorted(titles)[:40], "descriptions": sorted(descs)[:20],
        "sitemap_files": sitemap, "robots_files": robots, "jsonld_files": files_with_jsonld[:20],
        "meta_files": files_with_meta[:20], "emails": sorted(emails)[:10], "phones": sorted(phones)[:5],
        "external_domains": ext_links.most_common(30), "keywords": _keywords(text_blob, 20),
        "issues": issues,
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
    return {
        "site_wide": site_wide,
        "page_issues": {k: v[:25] for k, v in issues.items()},
        "broken_internal": d["broken_internal"],
        "broken_outbound": d["broken_outbound"],
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
    out = []
    for tu, tp in sorted(pages.items(), key=lambda kv: inbound[kv[0]]):
        kws = [k for k in _keywords(" ".join(filter(None, [tp["title"], *tp["h1"], tp["meta_description"]])), 8)
               if not set(k.split()) & (brand | common)][:4]
        linked_from = {su for su, sp in pages.items() if any(l["href"] == tu for l in sp["links"])}
        for su, sp in pages.items():
            if su == tu or su in linked_from:
                continue
            txt = sp["text_sample"].lower()
            hit = next((k for k in kws if k in txt), None)
            if hit:
                out.append({"from": su, "to": tu, "anchor": hit, "target_inbound_now": inbound[tu]})
                break
        if len(out) >= limit:
            break
    return out


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
            for k in kw[:3]:
                queries.append({"type": group, "query": t.format(kw=k, loc=loc).strip()})
            if "{kw}" not in t:
                break
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
            "Run footprint queries with web search; qualify each result with qualify_prospect; add good ones via tracker_add.",
            "Aim for relevance over volume: 10 relevant links beat 200 junk ones.",
        ],
    }


@mcp.tool()
async def qualify_prospect(url: str, my_domain: str = "") -> dict:
    """Fetch a prospect page and score it: is it live/indexable, does it accept guest posts or list
    resources, does it already link to you, outbound-link density (spam signal), contact info found."""
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=20) as c:
        try:
            r = await c.get(url)
        except Exception as e:
            return {"url": url, "ok": False, "error": str(e)}
    if r.status_code >= 400 or "html" not in r.headers.get("content-type", ""):
        return {"url": url, "ok": False, "status": r.status_code}
    p = _parse_page(str(r.url), r.text)
    low = r.text.lower()
    dom = _domain(str(r.url))
    ext = [l for l in p["links"] if _domain(l["href"]) != dom]
    signals = {
        "write_for_us": bool(re.search(r"write for us|guest post|contribute|submit (an )?article|guest author", low)),
        "resource_page": bool(re.search(r"resources|useful links|recommended (tools|sites)|tools we (use|love)", low)),
        "directory": bool(re.search(r"add (your )?(listing|business|site)|submit (your )?(site|listing|business)", low)),
        "sponsored_only": bool(re.search(r"sponsored post|paid post|price list for (guest|post)", low)),
        "noindex": bool(p["robots"] and "noindex" in p["robots"].lower()),
        "casino_pharma_spam": bool(re.search(r"casino|betting|viagra|cialis|payday loan|escort", low)),
    }
    already = [l for l in p["links"] if my_domain and _domain(l["href"]) == _domain(my_domain)]
    score = 50 + 15 * signals["write_for_us"] + 10 * signals["resource_page"] + 10 * signals["directory"]
    score -= 40 * signals["noindex"] + 50 * signals["casino_pharma_spam"] + 15 * signals["sponsored_only"]
    score -= 15 if len(ext) > 150 else 0
    score += 5 if p["word_count"] > 800 else 0
    return {
        "url": str(r.url), "ok": True, "title": p["title"], "lang": p["lang"], "signals": signals,
        "outbound_links": len(ext), "word_count": p["word_count"], "contact_emails": p["emails"],
        "already_links_to_you": already, "score_0_100": max(0, min(100, score)),
        "verdict": "skip" if score < 40 else ("good" if score >= 65 else "maybe"),
    }


@mcp.tool()
def build_submission_kit(domain: str, business_name: str = "", category: str = "", phone: str = "",
                         email: str = "", address: str = "", city: str = "", founded: str = "",
                         services: list[str] | None = None, socials: list[str] | None = None,
                         save: bool = True) -> dict:
    """Build a consistent NAP + description kit for directory/citation submissions, merging the cached
    scan profile with any fields you pass (passed values win). Saves Markdown + JSON to the data folder.
    Review and rewrite descriptions in your own voice before submitting."""
    d = _load(CACHE / f"{_domain(domain)}.json", {}) or {}
    pr = d.get("profile", {})
    a = pr.get("address") or {}
    kit = {
        "business_name": business_name or pr.get("name"),
        "website": pr.get("website") or f"https://{_domain(domain)}",
        "category": category or (pr.get("keywords") or [""])[0],
        "phone": phone or pr.get("phone"),
        "email": email or pr.get("email"),
        "address": address or ", ".join(v for v in a.values() if v) or None,
        "city": city or a.get("addressLocality"),
        "founded": founded or None,
        "services": services or (pr.get("keywords") or [])[:8],
        "social_profiles": socials or pr.get("same_as") or [],
        "logo": pr.get("logo"),
    }
    base = (pr.get("description") or "").strip()
    svc = ", ".join(kit["services"][:5])
    kit["descriptions"] = {
        "tagline_60": (base or f"{kit['business_name']} - {kit['category']}")[:60],
        "short_160": (base or f"{kit['business_name']} provides {svc}.")[:160],
        "long_draft": (f"{kit['business_name']} is a {kit['category']} business"
                       + (f" based in {kit['city']}" if kit["city"] else "")
                       + (f", founded in {kit['founded']}" if kit["founded"] else "")
                       + f". We offer {svc}. {base}").strip(),
    }
    missing = [k for k in ("business_name", "phone", "email", "address", "city") if not kit[k]]
    kit["missing_fields"] = missing
    kit["rules"] = ["Use this exact NAP everywhere - no abbreviations that differ between sites.",
                    "Use the homepage or the most relevant service page as the link URL.",
                    "Upload the same logo and pick the closest primary category on each site."]
    if save:
        out = DATA_DIR / f"submission_kit_{_domain(domain)}"
        _save(out.with_suffix(".json"), kit)
        md = [f"# Submission kit - {kit['business_name']}", ""]
        md += [f"- **{k.replace('_', ' ').title()}:** {v if not isinstance(v, list) else ', '.join(v)}"
               for k, v in kit.items() if k not in ("descriptions", "rules", "missing_fields")]
        md += ["", "## Descriptions"] + [f"**{k}:** {v}" for k, v in kit["descriptions"].items()]
        md += ["", "## Rules"] + [f"- {r}" for r in kit["rules"]]
        if missing:
            md += ["", f"**Missing:** {', '.join(missing)}"]
        out.with_suffix(".md").write_text("\n".join(md), "utf-8")
        kit["saved_to"] = [str(out.with_suffix(".json")), str(out.with_suffix(".md"))]
    return kit


@mcp.tool()
def draft_outreach(template: str, my_site: str, my_name: str, target_site: str = "",
                   contact_name: str = "", topic: str = "", my_page: str = "", broken_url: str = "",
                   extra: str = "") -> dict:
    """Draft a personalised outreach email. template: guest_post | resource_page | broken_link |
    unlinked_mention | partner | testimonial | local_press. Returns subject + body to edit and send
    yourself (this tool never sends email)."""
    t = OUTREACH_TEMPLATES.get(template)
    if not t:
        return {"error": f"Unknown template. Use one of: {', '.join(OUTREACH_TEMPLATES)}"}
    vals = {"my_site": my_site, "my_name": my_name, "target_site": target_site or "your site",
            "contact": contact_name or "there", "topic": topic or "a topic your readers care about",
            "my_page": my_page or my_site, "broken_url": broken_url or "[broken link]", "extra": extra}
    return {"subject": t["subject"].format(**vals), "body": t["body"].format(**vals).strip(),
            "tips": ["Personalise the first line with something specific from their site.",
                     "Send from your domain email, keep it under 150 words, follow up once after 5-7 days."]}


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
    e = {"id": (max([x["id"] for x in tr], default=0) + 1), "url": url, "kind": kind, "site": _domain(site),
         "status": status, "contact": contact, "notes": notes, "added": _now(), "updated": _now()}
    tr.append(e)
    _save(TRACKER, tr)
    return {"ok": True, "entry": e}


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
