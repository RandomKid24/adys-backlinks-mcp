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

# Ordered by how well they usually work for Indian/local businesses: lists and local first.
FOOTPRINTS = {
    "roundups_and_lists": [
        'top {kw} companies in {loc}',
        'best {kw} companies {loc}',
        '{kw} companies in {loc} list',
        'top {kw} companies in India',
        'best {kw} startups India',
        '{kw} "expert roundup"',
    ],
    "local": [
        '{loc} business directory',
        '{loc} IT companies list',
        '{loc} startups list',
        '{loc} chamber of commerce members',
        '{loc} industrial association members',
        '{loc} local news business',
        '"{loc}" {kw} blog',
    ],
    "guest_post": [
        '{kw} "write for us"',
        '{kw} "guest post guidelines"',
        '{kw} "become a contributor"',
        'intitle:"write for us" technology India',
    ],
    "resource_page": [
        '{kw} inurl:resources',
        '{kw} "useful links"',
        '{kw} intitle:"resources" "tools"',
    ],
    "podcasts_and_interviews": [
        '{kw} podcast "be a guest"',
        'India founder interview {kw}',
    ],
    "partners_and_tools": [
        '{kw} "technology partners"',
        '{kw} "partner program"',
    ],
    "events_and_education": [
        '{loc} tech meetup',
        '{loc} college "industry partner"',
        '{loc} hackathon sponsor',
    ],
}

# Placeholders: {contact} {target_site} {topic} {my_site} {my_name} {my_page} {broken_url} {proof} {hook}
# Rules for these templates: never claim a relationship that doesn't exist, keep it short, give the reader
# a reason that's about them. {hook} is one personalised sentence about their page (written by Claude).
OUTREACH_TEMPLATES = {
    "guest_post": {
        "needs": ["topic"],
        "subject": "Article idea for {target_site}: {topic}",
        "body": """
Hi {contact},

{hook}

I'd like to write an original article for {target_site}: "{topic}". It would be based on real project
work, practical, and not promotional. I'm happy to follow your guidelines, and a short author bio
with a link to {my_site} is all I'd ask for.
{proof}
Would that be a fit? I can send an outline first.

Thanks,
{my_name}
{my_site}
""",
    },
    "list_inclusion": {
        "needs": ["proof"],
        "subject": "For your list on {target_site}",
        "body": """
Hi {contact},

{hook}

If you update the list, I'd like {my_site} to be considered. A few facts that may help:
{proof}

Happy to send anything else you need to evaluate us. No pressure either way.

Thanks,
{my_name}
{my_site}
""",
    },
    "resource_page": {
        "needs": ["my_page", "topic"],
        "subject": "A resource for your {topic} list",
        "body": """
Hi {contact},

{hook}

We published a page that covers {topic}: {my_page}
It might be useful for your readers. Completely fine if it isn't a fit.

Thanks,
{my_name}
{my_site}
""",
    },
    "broken_link": {
        "needs": ["broken_url", "my_page"],
        "subject": "Broken link on {target_site}",
        "body": """
Hi {contact},

{hook}

Quick heads-up: the link to {broken_url} on that page no longer works.

If you want a replacement, {my_page} covers the same topic and is kept up to date.
Either way, thought you'd want to know about the broken link.

{my_name}
{my_site}
""",
    },
    "unlinked_mention": {
        "needs": [],
        "subject": "Thanks for the mention",
        "body": """
Hi {contact},

{hook}

Thanks for mentioning us on {target_site}. Would you be open to linking the mention to {my_site},
so readers can find us easily?

Thanks again,
{my_name}
""",
    },
    "partner": {
        "needs": ["topic"],
        "subject": "Possible collaboration: {topic}",
        "body": """
Hi {contact},

{hook}

I run {my_site}. I think there's a natural fit between what you do and our work on {topic}.
A few ideas, whichever is useful to you: a joint case study or article, listing each other on
partner/integration pages, or referring clients where the other is the better fit.
{proof}
Open to a quick chat?

{my_name}
{my_site}
""",
    },
    "testimonial": {
        "needs": ["topic"],
        "subject": "A testimonial for {target_site}",
        "body": """
Hi {contact},

We use {target_site} for {topic}, and it's genuinely been helpful.
If you collect customer testimonials, I'd be happy to write a short honest one. You're welcome to
link it to {my_site}.

{my_name}
""",
    },
    "local_press": {
        "needs": ["topic"],
        "subject": "Local story idea: {topic}",
        "body": """
Hi {contact},

{hook}

Story idea for your readers: {topic}.
{proof}
I'm {my_name} from {my_site}, based locally. Happy to share details, photos or a quote.

{my_name}
{my_site}
""",
    },
}
