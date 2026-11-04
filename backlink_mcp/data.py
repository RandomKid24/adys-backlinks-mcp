"""Curated opportunity data. Edit freely - add niche sites you trust.
priority: 5 = do first. region: 'global' or ISO country code. Link attributes (follow/nofollow) change
over time, so they're not listed - use verify_backlink after your profile goes live."""

def _d(name, url, tags, region="global", priority=3, notes=""):
    return {"name": name, "url": url, "tags": tags, "region": region, "priority": priority, "notes": notes}

DIRECTORIES = [
    # --- core citations (every business)
    _d("Google Business Profile", "https://www.google.com/business/", ["general", "local"], priority=5,
       notes="Most important local citation. Verify, add categories, services, photos."),
    _d("Bing Places", "https://www.bingplaces.com/", ["general", "local"], priority=5, notes="Can import from Google Business Profile."),
    _d("Apple Business Connect", "https://businessconnect.apple.com/", ["general", "local"], priority=4),
    _d("LinkedIn Company Page", "https://www.linkedin.com/company/setup/new/", ["general"], priority=5),
    _d("Facebook Page", "https://www.facebook.com/pages/create", ["general", "local"], priority=4),
    _d("Instagram Business", "https://www.instagram.com/", ["general", "local"], priority=3),
    _d("YouTube Channel", "https://www.youtube.com/", ["general"], priority=3, notes="Link in channel About + video descriptions."),
    _d("Crunchbase", "https://www.crunchbase.com/", ["general", "startup", "software"], priority=3),
    _d("Trustpilot", "https://business.trustpilot.com/", ["general"], priority=3),
    _d("Foursquare (Places)", "https://foursquare.com/", ["local"], priority=2),
    # --- India
    _d("Justdial", "https://www.justdial.com/Free-Listing", ["general", "local"], "IN", 5),
    _d("Sulekha", "https://www.sulekha.com/", ["local", "it", "education", "beauty", "healthcare"], "IN", 4),
    _d("IndiaMART", "https://seller.indiamart.com/", ["manufacturing", "b2b", "it", "software"], "IN", 5),
    _d("TradeIndia", "https://www.tradeindia.com/", ["manufacturing", "b2b"], "IN", 4),
    _d("ExportersIndia", "https://www.exportersindia.com/", ["manufacturing", "b2b"], "IN", 3),
    _d("Startup India", "https://www.startupindia.gov.in/", ["startup", "software", "saas"], "IN", 4,
       notes="DPIIT recognition + profile on a .gov.in domain."),
    _d("Udyam Registration", "https://udyamregistration.gov.in/", ["general", "manufacturing"], "IN", 2,
       notes="MSME registration - useful for trust, not a link."),
    _d("AmbitionBox", "https://www.ambitionbox.com/", ["general", "it", "software"], "IN", 2),
    _d("Glassdoor India", "https://www.glassdoor.co.in/", ["general", "it", "software"], "IN", 2),
    _d("Zomato for Business", "https://www.zomato.com/partner-with-us", ["food"], "IN", 5),
    _d("Swiggy Partner", "https://partner.swiggy.com/", ["food"], "IN", 4),
    _d("Practo", "https://www.practo.com/providers", ["healthcare"], "IN", 5),
    _d("Shiksha", "https://www.shiksha.com/", ["education"], "IN", 3),
    _d("MakeMyTrip Connect", "https://connect.makemytrip.com/", ["hospitality"], "IN", 4),
    # --- software / IT services / agency
    _d("Clutch", "https://clutch.co/", ["software", "it", "agency", "design"], priority=5, notes="Needs client reviews; strong for B2B agencies."),
    _d("GoodFirms", "https://www.goodfirms.co/", ["software", "it", "agency", "design"], priority=5),
    _d("DesignRush", "https://www.designrush.com/", ["agency", "design", "software"], priority=4),
    _d("The Manifest", "https://themanifest.com/", ["agency", "software", "it"], priority=3),
    _d("TechBehemoths", "https://techbehemoths.com/", ["agency", "software", "it"], priority=3),
    _d("Sortlist", "https://www.sortlist.com/", ["agency", "design"], priority=3),
    _d("G2 (for your products)", "https://sell.g2.com/", ["saas", "software"], priority=4),
    _d("Capterra / GetApp", "https://www.capterra.com/vendors/", ["saas", "software"], priority=4),
    _d("SaaSHub", "https://www.saashub.com/", ["saas"], priority=3),
    _d("AlternativeTo", "https://alternativeto.net/", ["saas", "software"], priority=3),
    _d("Product Hunt", "https://www.producthunt.com/", ["saas", "startup", "software"], priority=4, notes="Launch a product/tool, not the agency."),
    _d("GitHub (org + README links)", "https://github.com/", ["software", "it"], priority=4, notes="Open-source a useful tool; link site from org profile."),
    _d("Dev.to", "https://dev.to/", ["software", "it"], priority=3, notes="Publish genuine technical posts with canonical/profile link."),
    _d("Hashnode", "https://hashnode.com/", ["software", "it"], priority=3),
    _d("Medium", "https://medium.com/", ["general", "software"], priority=2),
    _d("Stack Overflow / Stack Exchange profile", "https://stackoverflow.com/", ["software"], priority=2, notes="Profile link only - never spam answers."),
    _d("F6S", "https://www.f6s.com/", ["startup", "software"], priority=2),
    # --- design
    _d("Behance", "https://www.behance.net/", ["design", "agency"], priority=3),
    _d("Dribbble", "https://dribbble.com/", ["design", "agency"], priority=3),
    _d("Awwwards (submit site)", "https://www.awwwards.com/", ["design", "agency"], priority=3, notes="Only for genuinely award-level sites."),
    # --- manufacturing / B2B global
    _d("Kompass", "https://www.kompass.com/", ["manufacturing", "b2b"], priority=3),
    _d("Europages", "https://www.europages.co.uk/", ["manufacturing", "b2b"], priority=2, notes="If you export to Europe."),
    _d("Alibaba (supplier)", "https://www.alibaba.com/", ["manufacturing", "b2b"], priority=2),
    _d("Thomasnet", "https://www.thomasnet.com/", ["manufacturing", "b2b"], "US", 3),
    # --- hospitality / food / beauty
    _d("Tripadvisor (owners)", "https://www.tripadvisor.com/Owners", ["hospitality", "food", "local"], priority=5),
    _d("Booking.com Partner", "https://join.booking.com/", ["hospitality"], priority=4),
    _d("Airbnb host", "https://www.airbnb.com/host", ["hospitality"], priority=3),
    _d("Fresha (salons)", "https://www.fresha.com/for-business", ["beauty"], priority=3),
    _d("Yelp for Business", "https://business.yelp.com/", ["local", "food", "beauty"], "US", 3),
]

FOOTPRINTS = {
    "guest_post": [
        '{kw} "write for us"',
        '{kw} "guest post" "guidelines"',
        '{kw} "submit an article"',
        '{kw} "become a contributor"',
        'intitle:"write for us" {kw} India',
    ],
    "resource_page": [
        '{kw} inurl:resources',
        '{kw} "useful links"',
        '{kw} intitle:"resources" "tools"',
    ],
    "local": [
        '{loc} business directory',
        '{loc} {kw} companies list',
        '{loc} chamber of commerce members',
        '{loc} startups list',
        '{loc} local news business',
        '"{loc}" {kw} blog',
    ],
    "roundups_and_lists": [
        'top {kw} companies {loc}',
        'best {kw} agencies {loc}',
        '{kw} "expert roundup"',
    ],
    "podcasts_and_interviews": [
        '{kw} podcast "be a guest"',
        '{kw} founder interview India',
    ],
    "partners_and_tools": [
        '{kw} "technology partners"',
        '{kw} "our customers" OR "case studies" -jobs',
    ],
    "events_and_education": [
        '{loc} tech meetup',
        '{loc} college "industry partner" {kw}',
        '{kw} hackathon sponsor India',
    ],
}

OUTREACH_TEMPLATES = {
    "guest_post": {
        "subject": "Article idea for {target_site}: {topic}",
        "body": """
Hi {contact},

I've been reading {target_site} and liked how you cover practical topics for your readers.

I'd like to write an original piece on "{topic}" - written from hands-on project experience, no fluff,
no promotional content. Happy to follow your guidelines and include a short author bio linking to {my_site}.

{extra}

Would that be a fit? I can send an outline first.

Thanks,
{my_name}
{my_site}
""",
    },
    "resource_page": {
        "subject": "Suggestion for your resources page",
        "body": """
Hi {contact},

I came across your resources page on {target_site} - genuinely useful list.

We published {my_page}, which covers {topic}. It might be a helpful addition for your readers.
{extra}

Either way, thanks for putting the list together.

{my_name}
{my_site}
""",
    },
    "broken_link": {
        "subject": "Broken link on {target_site}",
        "body": """
Hi {contact},

Quick heads-up: while reading {target_site} I noticed a link to {broken_url} that no longer works.

If you're looking for a replacement, our page {my_page} covers {topic} and is kept up to date.
No worries if it isn't a fit - just wanted to flag the broken link.

{my_name}
{my_site}
""",
    },
    "unlinked_mention": {
        "subject": "Thanks for mentioning us",
        "body": """
Hi {contact},

Thanks for mentioning us on {target_site} - really appreciate it.

Would you be open to linking the mention to {my_site} so readers can find us easily?
{extra}

Thanks again,
{my_name}
""",
    },
    "partner": {
        "subject": "Partner listing - {my_site} x {target_site}",
        "body": """
Hi {contact},

We've been working with {target_site} on {topic}, and it's gone well.
If you have a partners / integrations / customers page, we'd be glad to be listed - and happy to feature
you on our side or write a short case study together.

{extra}

{my_name}
{my_site}
""",
    },
    "testimonial": {
        "subject": "A testimonial for {target_site}",
        "body": """
Hi {contact},

We've been using {target_site} for {topic} and it's been genuinely helpful.
If you collect customer testimonials, I'd be happy to write a short one (and you're welcome to link it to {my_site}).

{extra}

{my_name}
""",
    },
    "local_press": {
        "subject": "Story idea: {topic}",
        "body": """
Hi {contact},

I run {my_site}, a local business. We recently {topic} and I thought it might interest your readers.
{extra}

Happy to share details, photos or a quote.

{my_name}
{my_site}
""",
    },
}
