"""End-to-end tests against a local fixture site. Run: pytest -q"""
import asyncio
import json
import re

import pytest

from backlink_mcp.countries import format_phone, region_matches, resolve_country


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def scanned(server, site, code_dir):
    r = run(server.scan_site(site["base"] + "/", 20, render="never"))
    server.save_project(site["domain"], niche="software erp", location="Nashik", country="India",
                        business_name="Acme Soft", keywords=["erp software", "manufacturing erp"])
    server.scan_codebase(str(code_dir), site=site["domain"])
    return r


# ------------------------------------------------------------------ pure helpers
@pytest.mark.parametrize("raw,country,display,e164", [
    ("(512) 555-0142", "US", "+1 512 555 0142", "+15125550142"),
    ("020 7946 0018", "UK", "+44 207 946 0018", "+442079460018"),
    ("9766183834", "India", "+91 97661 83834", "+919766183834"),
    ("919766183834", "IN", "+91 97661 83834", "+919766183834"),
    ("050 123 4567", "UAE", "+971 50 123 4567", "+971501234567"),
    ("030 1234567", "DE", "+49 30 123 4567", "+49301234567"),
])
def test_phone_formats(raw, country, display, e164):
    assert format_phone(raw, country) == (display, e164)


def test_country_aliases():
    assert resolve_country("uk") == "GB" and resolve_country("United States") == "US"
    assert resolve_country("UAE") == "AE" and resolve_country("Narnia") is None
    assert region_matches("EU", "DE") and not region_matches("EU", "GB") and region_matches(["US", "CA"], "CA")


@pytest.mark.parametrize("niche,must,must_not", [
    ("home builder", {"trades"}, {"saas"}),
    ("saas form builder", {"saas"}, {"trades", "agency"}),
    ("software erp", {"agency", "software"}, set()),
    ("dentist", {"healthcare"}, set()),
    ("ai writing tool", {"ai"}, set()),
])
def test_niche_tags(server, niche, must, must_not):
    tags = server._niche_tags(niche)
    assert must <= tags and not (must_not & tags)


def test_placeholder_and_email_filters(server):
    assert server._is_placeholder("+91 XXXXXXXXXX") and server._is_placeholder("20XX")
    assert server._is_placeholder("your full address") and not server._is_placeholder("Plot 12, MIDC")
    assert server._clean_emails(["test@test.com", "you@company.com", "i@izs.me", "Hello@Acme.test"]) == ["hello@acme.test"]


# ------------------------------------------------------------------ crawl + audit
def test_scan_profile_and_sitemap(scanned, site):
    p = scanned["profile"]
    assert p["name"] == "Acme Soft" and p["email"] == "hello@acme.test"
    assert "acme" not in " ".join(p["keywords"])
    sh = scanned["sitemap_health"]
    assert len(sh["sources"]) == 2  # index + child sitemap, found via robots.txt
    assert any(u.endswith("/gone") for u in sh["listed_but_broken"])
    assert any(u.endswith("/admin") for u in sh["listed_but_blocked_by_robots"])


def test_audit_priority_fixes(server, scanned, site):
    a = server.seo_link_audit(site["domain"])
    text = " ".join(a["priority_fixes"])
    assert 0 <= a["health_score"] <= 100 and a["grade"] in "ABCDF"
    assert "Book a Demo" in text and "Schedule Demo" in text            # dead buttons
    assert "@yourtwitterhandle" in text                                 # template placeholder
    assert "LocalBusiness" in text and "SoftwareApplication" not in text  # services company, not a product
    assert "/gone" in text and "http://127.0.0.1" not in text           # readable paths in messages
    assert a["priority_fixes"][0].startswith(("2 button", "Fix ")) or "noindex" in a["priority_fixes"][0]


def test_scan_codebase(server, code_dir):
    c = server.scan_codebase(str(code_dir))
    assert c["emails"] == [] and "React Router" in c["framework"]
    assert c["case_duplicate_routes"] == {"/about": ["/About", "/about"]}


# ------------------------------------------------------------------ content & links
def test_internal_links_have_exact_location(server, scanned, site):
    out = [x for x in server.internal_link_suggestions(site["domain"]) if "placement" in x]
    erp = next(x for x in out if x["link_to"].endswith("/product/erp"))
    assert erp["anchor_text"].lower() == "manufacturing erp" and erp["section"] == "What we build"
    assert '<a href="/product/erp">' in erp["sentence_with_link"]
    assert erp["code_location"][0] == {"file": "src/pages/Home.tsx", "line": 6}
    assert not any(x["link_to"].rstrip("/") == site["base"] for x in out)  # never targets the homepage


def test_content_plan(server, scanned, site):
    plan = server.content_plan(site["domain"], url="/contact")[0]
    heads = [s["heading"] for s in plan["sections_to_add"]]
    assert plan["page_type"] == "contact" and "Contact details" in heads and "Opening hours" in heads


# ------------------------------------------------------------------ opportunities
def test_find_opportunities_localised(server):
    o = server.find_opportunities("plumber", "Manchester", "UK")
    names = [d["name"] for d in o["citations_and_directories"]]
    assert names[0] == "Checkatrade" and "Yell" in names and "Justdial" not in names
    assert o["search_footprints"][0]["query"] == "best plumber in Manchester"
    assert "error" in server.find_opportunities("dentist", "", "Narnia")


def test_competitor_and_brand_queries(server):
    server.save_project("forms.test", niche="saas form builder", country="US", business_name="FormCo",
                        competitors=["formspree.io"])
    qs = [q["query"] for q in server.find_opportunities(site="forms.test")["search_footprints"]]
    assert '"Formspree alternatives"' in qs and '"FormCo" -site:forms.test' in qs


def test_custom_directory_scoped_to_city(server):
    server.add_custom_directory("Austin Chamber", "https://www.austinchamber.com/", ["general", "local"], "US", 5,
                                location="Austin")
    names = lambda loc: [d["name"] for d in server.find_opportunities("dentist", loc, "US")["citations_and_directories"]]
    assert "Austin Chamber" in names("Austin") and "Austin Chamber" not in names("Dallas")


def test_qualify_prospects(server, scanned, site):
    good = run(server.qualify_prospect(site["base"] + "/ext/roundup", "acme.test", ["erp"]))
    assert good["verdict"] == "good" and good["recommended_template"] == "list_inclusion"
    assert good["contact_emails"] == ["content@roundup.test"]
    spam = run(server.qualify_prospect(site["base"] + "/ext/spam", "acme.test"))
    assert spam["verdict"] == "skip" and spam["signals"]["spam_outbound_links"]


# ------------------------------------------------------------------ kit, schema, outreach
def test_kit_rejects_placeholders(server, scanned, site):
    k = server.build_submission_kit(site["domain"], phone="+91 XXXXXXXXXX", address="your full address", founded="20XX")
    assert set(k["rejected_placeholders"]) == {"phone", "address", "founded"}
    assert k["category"] == "Software Company" and k["city"] == "Nashik" and not k["ready_to_submit"]


def test_saas_schema(server):
    r = server.generate_schema("forms.test", business_type="SoftwareApplication",
                               offers=[{"name": "Starter", "price": "$9"}, {"name": "Pro", "price": "29"}])
    data = json.loads(re.search(r"\{.*\}", r["script_tag"], re.S).group(0))
    app = next(x for x in data["@graph"] if x["@type"] == "SoftwareApplication")
    assert app["offers"]["lowPrice"] == "9" and app["offers"]["priceCurrency"] == "USD"
    assert app["publisher"]["@id"].endswith("#organization")


def test_outreach_warnings(server):
    bad = server.draft_outreach("local_press", "acme.test", "Ady", topic="Top IT companies in Nashik")
    assert not bad["ready_to_send"] and any("list title" in w for w in bad["warnings"])
    ok = server.draft_outreach("list_inclusion", "acme.test", "Ady", target_site="Blog", contact_name="Priya",
                               hook="Your list was useful.", proof=["Founded 2025"])
    assert ok["ready_to_send"] and "- Founded 2025" in ok["body"]


# ------------------------------------------------------------------ tracker, verification, reporting
def test_tracker_verify_profile_and_actions(server, site):
    s = server
    a = s.tracker_add(site["base"] + "/ext/linker-follow", "mention", "acme.test", status="submitted")["entry"]
    b = s.tracker_add(site["base"] + "/ext/linker-nofollow", "mention", "acme.test", status="pitched")["entry"]
    assert b["follow_up_on"] > s._today()
    assert run(s.verify_backlink(a["url"], "acme.test"))["any_follow"]
    assert not run(s.verify_backlink(b["url"], "acme.test"))["any_follow"]
    s.save_project("acme.test", business_name="Acme Soft", keywords=["erp software"])
    lp = s.link_profile("acme.test")
    assert lp["live_links"] == 2 and lp["anchor_mix_percent"]["branded"] == 50
    assert any("exact-match" in w for w in lp["warnings"])
    c = s.tracker_add("https://blog.example.org/x", "guest_post", "acme.test", status="pitched")["entry"]
    s.tracker_update(c["id"], follow_up_in_days=-1)
    assert any(f"#{c['id']}" in x for x in s.next_actions("acme.test")["projects"][0]["actions"])
    s.tracker_update(c["id"], followed_up=True)
    assert s.tracker_update(c["id"], followed_up=True)["entry"]["status"] == "cold"


def test_export_report(server, scanned, site, tmp_path):
    r = server.export_report(site["domain"], prepared_by="BeForth")
    html = open(r["file"]).read()
    assert r["ok"] and "<html" in html and "Fix first" in html and "BeForth" in html and "Checkatrade" not in html


def test_tool_registry(server):
    tools = run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert len(tools) == 23 and {"export_report", "next_actions", "link_profile", "content_plan"} <= names
    assert all(t.description and len(t.description) > 40 for t in tools)


# ------------------------------------------------------------------ optional JS rendering
def _browser_ok():
    from backlink_mcp import render
    if not render.available():
        return False

    async def probe():
        async with render.Renderer("t") as r:
            return r.ok
    try:
        return asyncio.run(probe())
    except Exception:
        return False


@pytest.mark.skipif(not _browser_ok(), reason="playwright/chromium not installed")
def test_js_rendered_backlink(server, site):
    r = run(server.verify_backlink(site["base"] + "/ext/spa", "acme.test"))
    assert r["live"] and r["links"][0]["anchor"] == "Acme Soft"
