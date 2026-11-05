"""Self-contained HTML report (no external files) - safe to email to a client or open offline."""
from __future__ import annotations

from html import escape as _e
from urllib.parse import urlparse

STATUS_ORDER = ["live", "submitted", "pitched", "todo", "lost", "cold", "rejected"]

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#16181d;--muted:#5f6672;--line:#e4e4e0;--accent:#2f5bea;
--good:#1f8a4c;--warn:#b26a00;--bad:#c2372f;--chip:#eef0f4}
@media (prefers-color-scheme:dark){:root{--bg:#111316;--card:#1a1d22;--ink:#e9eaee;--muted:#9aa1ad;
--line:#2a2e35;--accent:#7b9bff;--good:#4cc27e;--warn:#e0a03a;--bad:#ff6b61;--chip:#252a31}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:32px 16px 64px}
header{display:flex;flex-wrap:wrap;gap:24px;align-items:center;justify-content:space-between;margin-bottom:24px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:18px;margin:0 0 12px}
.sub{color:var(--muted);font-size:13px}
.score{display:flex;align-items:center;gap:14px}
.ring{width:84px;height:84px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:26px;
background:conic-gradient(var(--c) calc(var(--p)*1%),var(--line) 0)}
.ring span{width:68px;height:68px;border-radius:50%;background:var(--card);display:grid;place-items:center}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.stat b{display:block;font-size:22px}.stat small{color:var(--muted)}
ol.fixes{margin:0;padding-left:22px}ol.fixes li{margin:6px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--chip);font-size:12px;white-space:nowrap}
.live{color:var(--good)}.lost,.rejected,.cold{color:var(--bad)}.pitched,.submitted{color:var(--warn)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code{background:var(--chip);padding:1px 5px;border-radius:4px;font-size:13px}
.muted{color:var(--muted)}.scroll{overflow-x:auto}
footer{margin-top:32px;color:var(--muted);font-size:12px;text-align:center}
"""


def _host(u: str) -> str:
    return urlparse(u).netloc or u


def _path(u: str) -> str:
    p = urlparse(u)
    return (p.path or "/") if p.netloc else u


def build(r: dict) -> str:
    a, pr, tr, lp = r.get("audit") or {}, r.get("project") or {}, r.get("tracker") or [], r.get("link_profile") or {}
    score = a.get("health_score")
    color = "var(--good)" if (score or 0) >= 75 else "var(--warn)" if (score or 0) >= 50 else "var(--bad)"
    title = r.get("client_name") or pr.get("name") or r["site"]
    status_counts = {s: sum(1 for e in tr if e["status"] == s) for s in STATUS_ORDER}
    out = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
           f"content='width=device-width,initial-scale=1'><title>SEO & Backlinks Report – {_e(title)}</title>"
           f"<style>{CSS}</style></head><body><div class='wrap'>"]
    out.append("<header><div>")
    out.append(f"<h1>{_e(title)}</h1><div class='sub'>{_e(r['site'])} · SEO & backlinks report · {_e(r['date'])}"
               + (f" · prepared by {_e(r['prepared_by'])}" if r.get("prepared_by") else "") + "</div>")
    meta = " · ".join(x for x in (pr.get("niche"), pr.get("location"), pr.get("country")) if x)
    if meta:
        out.append(f"<div class='sub'>{_e(meta)}</div>")
    out.append("</div>")
    if score is not None:
        out.append(f"<div class='score'><div class='ring' style='--p:{score};--c:{color}'><span>{score}</span></div>"
                   f"<div><b>Site health: {_e(a.get('grade', ''))}</b><div class='sub'>{a.get('pages_audited', 0)} pages "
                   f"audited</div></div></div>")
    out.append("</header>")

    out.append("<div class='stats'>")
    for label, val in (("Live backlinks", status_counts["live"]), ("In progress", status_counts["submitted"] + status_counts["pitched"]),
                       ("To do", status_counts["todo"]), ("Lost", status_counts["lost"]),
                       ("Referring domains", lp.get("referring_domains", 0)), ("Fixes to make", len(a.get("priority_fixes", [])))):
        out.append(f"<div class='stat'><small>{_e(label)}</small><b>{val}</b></div>")
    out.append("</div>")

    if a.get("priority_fixes"):
        out.append("<div class='card'><h2>Fix first (most important at the top)</h2><ol class='fixes'>")
        out += [f"<li>{_e(x)}</li>" for x in a["priority_fixes"][:20]]
        out.append("</ol></div>")

    links = [x for x in r.get("link_suggestions") or [] if x.get("placement")]
    if links:
        out.append("<div class='card'><h2>Internal links to add</h2><div class='scroll'><table><tr><th>On page</th>"
                   "<th>Link to</th><th>Anchor text</th><th>Where</th></tr>")
        for x in links[:12]:
            where = _e(x.get("section") or "")
            if x.get("code_location"):
                c = x["code_location"][0]
                where += f"<br><code>{_e(c['file'])}:{c['line']}</code>"
            if x["placement"] == "add_sentence":
                where += "<br><span class='muted'>add a new sentence</span>"
            out.append(f"<tr><td>{_e(_path(x['add_link_on_page']))}</td><td>{_e(_path(x['link_to']))}</td>"
                       f"<td>{_e(x['anchor_text'])}</td><td>{where}</td></tr>")
        out.append("</table></div></div>")

    plans = [x for x in r.get("content_plan") or [] if x.get("page")]
    if plans:
        out.append("<div class='card'><h2>Pages that need more content</h2><div class='scroll'><table><tr><th>Page</th>"
                   "<th>Words now → target</th><th>Sections to add</th></tr>")
        for x in plans[:8]:
            secs = ", ".join(s["heading"] for s in x["sections_to_add"][:6]) or "-"
            out.append(f"<tr><td>{_e(_path(x['page']))} <span class='chip'>{_e(x['page_type'])}</span></td>"
                       f"<td>{x['words_now']} → {x['target_words']}</td><td>{_e(secs)}</td></tr>")
        out.append("</table></div></div>")

    dirs = r.get("directories") or []
    if dirs:
        done = {_host(e["url"]).replace("www.", "") for e in tr}
        out.append("<div class='card'><h2>Where to list the business</h2><div class='scroll'><table><tr><th>#</th>"
                   "<th>Site</th><th>Why</th><th>Status</th></tr>")
        for i, d in enumerate(dirs[:15], 1):
            st = "tracked" if _host(d["url"]).replace("www.", "") in done else ""
            out.append(f"<tr><td>{i}</td><td><a href='{_e(d['url'])}'>{_e(d['name'])}</a></td>"
                       f"<td class='muted'>{_e(d.get('notes') or ('niche directory' if d.get('why') == 'niche' else 'core listing'))}</td>"
                       f"<td>{'<span class=chip>' + st + '</span>' if st else ''}</td></tr>")
        out.append("</table></div></div>")

    if tr:
        out.append("<div class='card'><h2>Backlink tracker</h2><div class='scroll'><table><tr><th>#</th><th>Site</th>"
                   "<th>Type</th><th>Status</th><th>Details</th></tr>")
        for e in sorted(tr, key=lambda e: (STATUS_ORDER.index(e["status"]) if e["status"] in STATUS_ORDER else 9, e["id"])):
            l = e.get("link") or {}
            det = []
            if l.get("anchor"):
                det.append(f"anchor “{_e(l['anchor'])}”")
            if l:
                det.append("follow" if l.get("follow") else "nofollow")
            if e.get("follow_up_on") and e["status"] in ("pitched", "submitted"):
                det.append(f"follow up {e['follow_up_on']}")
            out.append(f"<tr><td>{e['id']}</td><td><a href='{_e(e['url'])}'>{_e(_host(e['url']))}</a></td>"
                       f"<td>{_e(e['kind'])}</td><td class='{_e(e['status'])}'>{_e(e['status'])}</td>"
                       f"<td class='muted'>{' · '.join(det)}</td></tr>")
        out.append("</table></div></div>")

    if lp.get("live_links"):
        mix = " · ".join(f"{_e(k.replace('_', ' '))} {v}%" for k, v in lp.get("anchor_mix_percent", {}).items())
        fol = lp.get("follow", {})
        out.append(f"<div class='card'><h2>Link profile</h2><p>{lp['live_links']} live links from "
                   f"{lp.get('referring_domains', 0)} domains · {fol.get('follow', 0)} follow / {fol.get('nofollow', 0)} nofollow"
                   f"</p><p class='muted'>Anchor mix: {mix}</p>")
        if lp.get("warnings"):
            out.append("<ul>" + "".join(f"<li>{_e(w)}</li>" for w in lp["warnings"]) + "</ul>")
        out.append("</div>")

    out.append("<footer>Generated with Ady's Backlinks MCP · white-hat only: no paid links, no spam</footer>")
    out.append("</div></body></html>")
    return "".join(out)
