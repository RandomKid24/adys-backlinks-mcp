"""Built-in opportunity data. Works for any business and country.

Don't edit this file for your own additions - put them in ~/.backlink-mcp/custom.json
(or use the add_custom_directory / add_custom_footprint tools) so updates never overwrite them.

Directory fields:
  priority: 5 = do first, 1 = nice to have
  region:   "global", an ISO country code ("IN", "US", "GB"...), a region ("EU", "GCC", "ANZ", "NA",
            "SEA", "EUROPE", "SOUTH_ASIA") or a list of those
  tags:     which niches it suits (see NICHE_TAGS)
Link attributes (follow/nofollow) change over time, so they aren't listed - use verify_backlink.
"""


def _d(name, url, tags, region="global", priority=3, notes=""):
    return {"name": name, "url": url, "tags": tags, "region": region, "priority": priority, "notes": notes}


DIRECTORIES = [
    # ------------------------------------------------ core citations: every business, every country
    _d("Google Business Profile", "https://www.google.com/business/", ["general", "local"], priority=5,
       notes="Most important local citation. Verify, add categories, services, photos."),
    _d("Bing Places", "https://www.bingplaces.com/", ["general", "local"], priority=5, notes="Can import from Google Business Profile."),
    _d("Apple Business Connect", "https://businessconnect.apple.com/", ["general", "local"], priority=4),
    _d("LinkedIn Company Page", "https://www.linkedin.com/company/setup/new/", ["general"], priority=5),
    _d("Facebook Page", "https://www.facebook.com/pages/create", ["general", "local"], priority=4),
    _d("Instagram Business", "https://www.instagram.com/", ["general", "local"], priority=3),
    _d("YouTube Channel", "https://www.youtube.com/", ["general"], priority=3, notes="Link in channel About + video descriptions."),
    _d("Pinterest Business", "https://business.pinterest.com/", ["design", "ecommerce", "food", "beauty", "events", "realestate"], priority=2),
    _d("Crunchbase", "https://www.crunchbase.com/", ["general", "startup", "software"], priority=3),
    _d("Trustpilot", "https://business.trustpilot.com/", ["general", "ecommerce"], priority=3),
    _d("Sitejabber", "https://www.sitejabber.com/", ["ecommerce"], priority=2),
    _d("Hotfrog", "https://www.hotfrog.com/", ["general", "local"], priority=2),
    _d("Foursquare (Places)", "https://foursquare.com/", ["local"], priority=2),
    _d("Glassdoor (employer)", "https://www.glassdoor.com/employers/", ["general", "software", "it"], priority=2),
    _d("Bark", "https://www.bark.com/", ["trades", "local", "legal", "events", "fitness", "agency", "design", "finance"],
       ["GB", "US", "CA", "AU", "NZ", "IE", "IN", "ZA", "SG"], 3),
    _d("Nextdoor Business", "https://business.nextdoor.com/", ["local", "trades"], ["US", "GB", "CA", "AU", "EUROPE"], 3),

    # ------------------------------------------------ general local directories by country
    _d("Justdial", "https://www.justdial.com/Free-Listing", ["general", "local"], "IN", 5),
    _d("Sulekha", "https://www.sulekha.com/", ["local", "it", "education", "beauty", "healthcare", "trades"], "IN", 4),
    _d("Udyam Registration", "https://udyamregistration.gov.in/", ["general", "manufacturing"], "IN", 2,
       notes="MSME registration - useful for trust, not a link."),
    _d("Better Business Bureau", "https://www.bbb.org/", ["general", "local"], "NA", 4),
    _d("Yellow Pages (US)", "https://www.yellowpages.com/", ["general", "local"], "US", 3),
    _d("Manta", "https://www.manta.com/", ["general", "local"], "US", 3),
    _d("ChamberofCommerce.com", "https://www.chamberofcommerce.com/", ["general", "local"], "US", 2),
    _d("YellowPages.ca", "https://www.yellowpages.ca/", ["general", "local"], "CA", 4),
    _d("Canada411", "https://www.canada411.ca/", ["general", "local"], "CA", 2),
    _d("Yell", "https://www.yell.com/", ["general", "local"], "GB", 5),
    _d("Thomson Local", "https://www.thomsonlocal.com/", ["general", "local"], "GB", 3),
    _d("FreeIndex", "https://www.freeindex.co.uk/", ["general", "local"], "GB", 3),
    _d("Scoot", "https://www.scoot.co.uk/", ["general", "local"], "GB", 2),
    _d("Yellow Pages (Australia)", "https://www.yellowpages.com.au/", ["general", "local"], "AU", 5),
    _d("True Local", "https://www.truelocal.com.au/", ["general", "local"], "AU", 4),
    _d("StartLocal", "https://www.startlocal.com.au/", ["general", "local"], "AU", 2),
    _d("Finda", "https://www.finda.co.nz/", ["general", "local"], "NZ", 3),
    _d("Yellow (NZ)", "https://yellow.co.nz/", ["general", "local"], "NZ", 4),
    _d("Yellow Pages UAE", "https://www.yellowpages-uae.com/", ["general", "local", "b2b"], "AE", 4),
    _d("Connect.ae", "https://www.connect.ae/", ["general", "local"], "AE", 3),
    _d("Gelbe Seiten", "https://www.gelbeseiten.de/", ["general", "local"], "DE", 5),
    _d("Das Örtliche", "https://www.dasoertliche.de/", ["general", "local"], "DE", 4),
    _d("11880.com", "https://www.11880.com/", ["general", "local"], "DE", 3),
    _d("PagesJaunes", "https://www.pagesjaunes.fr/", ["general", "local"], "FR", 5),
    _d("Páginas Amarillas", "https://www.paginasamarillas.es/", ["general", "local"], "ES", 4),
    _d("PagineGialle", "https://www.paginegialle.it/", ["general", "local"], "IT", 4),
    _d("Brabys", "https://www.brabys.com/", ["general", "local"], "ZA", 3),

    # ------------------------------------------------ software / IT / agencies / startups
    _d("Clutch", "https://clutch.co/", ["agency", "it", "design"], priority=5, notes="Needs client reviews; strong for B2B agencies."),
    _d("GoodFirms", "https://www.goodfirms.co/", ["software", "it", "agency", "design"], priority=5),
    _d("DesignRush", "https://www.designrush.com/", ["agency", "it", "design"], priority=4),
    _d("The Manifest", "https://themanifest.com/", ["agency", "it", "design"], priority=3),
    _d("TechBehemoths", "https://techbehemoths.com/", ["agency", "it", "design"], priority=3),
    _d("Sortlist", "https://www.sortlist.com/", ["agency", "design"], priority=3),
    _d("G2 (for your products)", "https://sell.g2.com/", ["saas", "software"], priority=4),
    _d("Capterra / GetApp", "https://www.capterra.com/vendors/", ["saas", "software"], priority=4),
    _d("SaaSHub", "https://www.saashub.com/", ["saas"], priority=3),
    _d("AlternativeTo", "https://alternativeto.net/", ["saas", "software"], priority=3),
    _d("Product Hunt", "https://www.producthunt.com/", ["saas", "startup", "software", "ecommerce"], priority=4,
       notes="Launch a product/tool, not the agency."),
    _d("BetaList", "https://betalist.com/", ["startup", "saas"], priority=2),
    _d("Wellfound", "https://wellfound.com/", ["startup", "software"], priority=3),
    _d("F6S", "https://www.f6s.com/", ["startup", "software"], priority=2),
    _d("GitHub (org + README links)", "https://github.com/", ["software", "it"], priority=4,
       notes="Open-source a useful tool; link your site from the org profile."),
    _d("Dev.to", "https://dev.to/", ["software", "it"], priority=3, notes="Publish genuine technical posts with a profile link."),
    _d("Hashnode", "https://hashnode.com/", ["software", "it"], priority=3),
    _d("Medium", "https://medium.com/", ["general", "software"], priority=2),
    _d("Stack Overflow profile", "https://stackoverflow.com/", ["software"], priority=2, notes="Profile link only - never spam answers."),
    # launch platforms & communities (products, tools, SaaS, dev tools, AI)
    _d("Indie Hackers (product page)", "https://www.indiehackers.com/products", ["saas", "startup"], priority=3),
    _d("Hacker News - Show HN", "https://news.ycombinator.com/showhn.html", ["saas", "startup", "dev"], priority=3,
       notes="Post once, when it's genuinely useful to developers; answer every comment."),
    _d("DevHunt", "https://devhunt.org/", ["dev", "saas"], priority=3),
    _d("Uneed", "https://www.uneed.best/", ["saas", "startup"], priority=2),
    _d("Peerlist Launchpad", "https://peerlist.io/launchpad", ["saas", "startup", "dev"], priority=2),
    _d("StackShare", "https://stackshare.io/", ["dev", "saas"], priority=2),
    _d("SourceForge (business software)", "https://sourceforge.net/software/", ["saas", "software"], priority=3),
    _d("Slant", "https://www.slant.co/", ["saas", "software", "dev"], priority=2),
    _d("npm package", "https://www.npmjs.com/", ["dev"], priority=3, notes="Publish an SDK/embed helper; link homepage in package.json."),
    _d("PyPI package", "https://pypi.org/", ["dev"], priority=2, notes="If you ship a Python SDK; set project URLs."),
    _d("Futurepedia", "https://www.futurepedia.io/", ["ai"], priority=3),
    _d("There's An AI For That", "https://theresanaiforthat.com/", ["ai"], priority=3),
    _d("Toolify", "https://www.toolify.ai/", ["ai"], priority=2),
    _d("SoftwareSuggest", "https://www.softwaresuggest.com/", ["saas", "software"], "IN", 4),
    _d("Techjockey", "https://www.techjockey.com/", ["saas", "software"], "IN", 3),
    _d("Startup India", "https://www.startupindia.gov.in/", ["startup", "software", "saas"], "IN", 4,
       notes="DPIIT recognition + profile on a .gov.in domain."),
    _d("AmbitionBox", "https://www.ambitionbox.com/", ["general", "it", "software"], "IN", 2),

    # ------------------------------------------------ design / creative
    _d("Behance", "https://www.behance.net/", ["design", "agency"], priority=3),
    _d("Dribbble", "https://dribbble.com/", ["design", "agency"], priority=3),
    _d("Awwwards (submit site)", "https://www.awwwards.com/", ["design", "agency"], priority=3, notes="Only for genuinely award-level sites."),

    # ------------------------------------------------ manufacturing / B2B / suppliers
    _d("Kompass", "https://www.kompass.com/", ["manufacturing", "b2b"], priority=3),
    _d("Alibaba (supplier)", "https://www.alibaba.com/", ["manufacturing", "b2b"], priority=2),
    _d("Europages", "https://www.europages.co.uk/", ["manufacturing", "b2b"], "EUROPE", 3),
    _d("Wer liefert was", "https://www.wlw.de/", ["manufacturing", "b2b"], ["DE", "CH"], 4),
    _d("Thomasnet", "https://www.thomasnet.com/", ["manufacturing", "b2b"], "NA", 4),
    _d("IndiaMART", "https://seller.indiamart.com/", ["manufacturing", "b2b", "it"], "IN", 5),
    _d("TradeIndia", "https://www.tradeindia.com/", ["manufacturing", "b2b"], "IN", 4),
    _d("ExportersIndia", "https://www.exportersindia.com/", ["manufacturing", "b2b"], "IN", 3),

    # ------------------------------------------------ restaurants / food
    _d("Tripadvisor (owners)", "https://www.tripadvisor.com/Owners", ["hospitality", "food"], priority=5),
    _d("OpenTable for restaurants", "https://restaurant.opentable.com/", ["food"], priority=3),
    _d("Uber Eats merchants", "https://merchants.ubereats.com/", ["food"], priority=3),
    _d("Yelp for Business", "https://business.yelp.com/", ["local", "food", "beauty", "trades", "healthcare"], ["US", "CA", "GB", "IE"], 4),
    _d("DoorDash merchants", "https://get.doordash.com/", ["food"], ["NA", "AU", "NZ"], 3),
    _d("Deliveroo partners", "https://restaurants.deliveroo.com/", ["food"], ["GB", "IE", "AE", "QA", "SG", "FR", "IT", "BE"], 3),
    _d("TheFork", "https://www.theforkmanager.com/", ["food"], "EUROPE", 3),
    _d("Talabat partners", "https://www.talabat.com/", ["food"], "GCC", 3),
    _d("Zomato for Business", "https://www.zomato.com/partner-with-us", ["food"], "IN", 5),
    _d("Swiggy Partner", "https://partner.swiggy.com/", ["food"], "IN", 4),

    # ------------------------------------------------ hotels / stays / travel
    _d("Booking.com Partner", "https://join.booking.com/", ["hospitality"], priority=4),
    _d("Airbnb host", "https://www.airbnb.com/host", ["hospitality"], priority=3),
    _d("MakeMyTrip Connect", "https://connect.makemytrip.com/", ["hospitality"], "IN", 4),

    # ------------------------------------------------ beauty / wellness / fitness
    _d("Fresha", "https://www.fresha.com/for-business", ["beauty", "fitness"], priority=3),
    _d("Booksy", "https://biz.booksy.com/", ["beauty"], priority=3),
    _d("Treatwell", "https://www.treatwell.co.uk/partners/", ["beauty"], "EUROPE", 3),
    _d("Vagaro", "https://www.vagaro.com/", ["beauty", "fitness"], ["US", "CA", "GB", "AU"], 3),
    _d("Mindbody", "https://www.mindbodyonline.com/", ["fitness", "beauty"], priority=3),
    _d("ClassPass partners", "https://classpass.com/partners", ["fitness"], priority=3),
    _d("Urban Company partner", "https://www.urbancompany.com/", ["beauty", "trades"], ["IN", "AE", "SG"], 3),

    # ------------------------------------------------ healthcare
    _d("Practo", "https://www.practo.com/providers", ["healthcare"], "IN", 5),
    _d("Zocdoc", "https://www.zocdoc.com/join", ["healthcare"], "US", 4),
    _d("Healthgrades", "https://www.healthgrades.com/", ["healthcare"], "US", 4),
    _d("RateMDs", "https://www.ratemds.com/", ["healthcare"], "NA", 2),

    # ------------------------------------------------ legal
    _d("Avvo", "https://www.avvo.com/", ["legal"], "US", 4),
    _d("Justia Lawyer Directory", "https://lawyers.justia.com/", ["legal"], "US", 4),
    _d("FindLaw", "https://lawyers.findlaw.com/", ["legal"], "US", 3),
    _d("Martindale-Hubbell", "https://www.martindale.com/", ["legal"], "US", 3),
    _d("Law Society - Find a Solicitor", "https://solicitors.lawsociety.org.uk/", ["legal"], "GB", 4,
       notes="Listing comes from your Law Society registration."),
    _d("LawRato", "https://lawrato.com/", ["legal"], "IN", 3),

    # ------------------------------------------------ real estate
    _d("Zillow (agents)", "https://www.zillow.com/", ["realestate"], "US", 4),
    _d("Realtor.com", "https://www.realtor.com/", ["realestate"], "US", 3),
    _d("Rightmove", "https://www.rightmove.co.uk/", ["realestate"], "GB", 4),
    _d("Zoopla", "https://www.zoopla.co.uk/", ["realestate"], "GB", 3),
    _d("realestate.com.au", "https://www.realestate.com.au/", ["realestate"], "AU", 4),
    _d("Domain", "https://www.domain.com.au/", ["realestate"], "AU", 3),
    _d("Bayut", "https://www.bayut.com/", ["realestate"], "AE", 4),
    _d("Property Finder", "https://www.propertyfinder.ae/", ["realestate"], "AE", 4),
    _d("99acres", "https://www.99acres.com/", ["realestate"], "IN", 4),
    _d("MagicBricks", "https://www.magicbricks.com/", ["realestate"], "IN", 4),
    _d("Housing.com", "https://housing.com/", ["realestate"], "IN", 3),

    # ------------------------------------------------ trades / home services / construction
    _d("Houzz Pro", "https://pro.houzz.com/", ["trades", "design", "realestate"], priority=4),
    _d("Angi", "https://www.angi.com/", ["trades"], "US", 4),
    _d("Thumbtack", "https://www.thumbtack.com/pro", ["trades", "events", "fitness"], "US", 4),
    _d("Porch", "https://pro.porch.com/", ["trades"], "US", 2),
    _d("HomeStars", "https://homestars.com/", ["trades"], "CA", 4),
    _d("Checkatrade", "https://www.checkatrade.com/", ["trades"], "GB", 5),
    _d("TrustATrader", "https://www.trustatrader.com/", ["trades"], "GB", 4),
    _d("MyBuilder", "https://www.mybuilder.com/", ["trades"], "GB", 3),
    _d("hipages", "https://hipages.com.au/", ["trades"], "AU", 4),
    _d("Oneflare", "https://www.oneflare.com.au/", ["trades", "events"], "AU", 3),

    # ------------------------------------------------ education
    _d("Shiksha", "https://www.shiksha.com/", ["education"], "IN", 3),
    _d("Niche (schools)", "https://www.niche.com/", ["education"], "US", 3),
    _d("GreatSchools", "https://www.greatschools.org/", ["education"], "US", 3),

    # ------------------------------------------------ weddings / events
    _d("The Knot (vendors)", "https://www.theknot.com/", ["events"], "US", 4),
    _d("WeddingWire (vendors)", "https://www.weddingwire.com/", ["events"], "US", 3),
    _d("Hitched (suppliers)", "https://www.hitched.co.uk/", ["events"], "GB", 4),
    _d("WedMeGood", "https://www.wedmegood.com/", ["events"], "IN", 4),

    # ------------------------------------------------ nonprofits
    _d("Candid (GuideStar)", "https://candid.org/", ["nonprofit"], "US", 4),
    _d("GlobalGiving", "https://www.globalgiving.org/", ["nonprofit"], priority=3),
    _d("GiveIndia", "https://www.giveindia.org/", ["nonprofit"], "IN", 3),
]

# niche word (substring of what the user types) -> directory tags
NICHE_TAGS = {
    "software": ["software", "it", "saas", "agency"], "it ": ["it", "software", "agency"], "it-": ["it", "software", "agency"],
    "saas": ["saas", "software", "startup"], "erp": ["software", "saas", "it"], "crm": ["software", "saas", "it"],
    "app": ["software", "it", "agency"], "web": ["agency", "it", "design"], "develop": ["software", "it", "agency"],
    "agency": ["agency", "design"], "marketing": ["agency"], "seo": ["agency"], "design": ["design", "agency"],
    "startup": ["startup"], "tech": ["software", "it", "startup"],
    " ai ": ["ai", "saas"], " ai-": ["ai", "saas"], "artificial intelligence": ["ai", "saas"], "gpt": ["ai", "saas"],
    "cms": ["saas", "software"], "platform": ["saas", "software"], "tool": ["saas"], "builder": ["saas"],
    "api": ["saas", "dev"], "sdk": ["dev"], "developer": ["dev", "software"], "devtool": ["dev", "saas"],
    "no-code": ["saas"], "nocode": ["saas"], "automation": ["saas"], "plugin": ["dev", "saas"], "extension": ["saas", "dev"],
    "manufactur": ["manufacturing", "b2b"], "industrial": ["manufacturing", "b2b"], "pharma": ["manufacturing", "b2b"],
    "machin": ["manufacturing", "b2b"], "supplier": ["manufacturing", "b2b"], "wholesale": ["b2b"], "export": ["b2b", "manufacturing"],
    "restaurant": ["food", "local"], "cafe": ["food", "local"], "bakery": ["food", "local"], "food": ["food", "local"],
    "catering": ["food", "events", "local"], "bar ": ["food", "local"],
    "salon": ["beauty", "local"], "spa": ["beauty", "local"], "beauty": ["beauty", "local"], "barber": ["beauty", "local"],
    "gym": ["fitness", "local"], "fitness": ["fitness", "local"], "yoga": ["fitness", "local"], "studio": ["fitness", "design"],
    "hotel": ["hospitality", "local"], "resort": ["hospitality", "local"], "homestay": ["hospitality", "local"],
    "travel": ["hospitality"], "tour": ["hospitality"],
    "clinic": ["healthcare", "local"], "dentist": ["healthcare", "local"], "orthodont": ["healthcare", "local"],
    "vet": ["healthcare", "local"], "pharmacy": ["healthcare", "local"], "optician": ["healthcare", "local"],
    "chiropract": ["healthcare", "local"], "therap": ["healthcare", "local"], "doctor ": ["healthcare", "local"], "doctor": ["healthcare", "local"], "dental": ["healthcare", "local"],
    "hospital": ["healthcare", "local"], "physio": ["healthcare", "local"], "health": ["healthcare"],
    "law": ["legal", "local"], "legal": ["legal", "local"], "attorney": ["legal", "local"], "solicitor": ["legal", "local"],
    "real estate": ["realestate", "local"], "realtor": ["realestate", "local"], "property": ["realestate", "local"],
    "plumb": ["trades", "local"], "electric": ["trades", "local"], "contractor": ["trades", "local"], "home builder": ["trades", "local"], "house builder": ["trades", "local"],
    "construction": ["trades", "local"], "roof": ["trades", "local"], "clean": ["trades", "local"], "interior": ["trades", "design", "local"],
    "architect": ["design", "trades"], "hvac": ["trades", "local"], "landscap": ["trades", "local"], "pest": ["trades", "local"],
    "school": ["education", "local"], "academy": ["education", "local"], "coaching": ["education", "local"],
    "tutor": ["education", "local"], "education": ["education"], "course": ["education"],
    "shop": ["ecommerce"], "store": ["ecommerce", "local"], "ecommerce": ["ecommerce"], "e-commerce": ["ecommerce"], "brand": ["ecommerce"],
    "wedding": ["events", "local"], "event": ["events", "local"], "photograph": ["events", "design", "local"],
    "account": ["finance", "local"], "tax": ["finance", "local"], "finance": ["finance"], "insurance": ["finance", "local"],
    "ngo": ["nonprofit"], "charity": ["nonprofit"], "nonprofit": ["nonprofit"], "non-profit": ["nonprofit"],
    "car": ["automotive", "local"], "auto": ["automotive", "local"], "garage": ["automotive", "trades", "local"],
}

# (keywords found in site text, directory-style category) - first match wins
CATEGORY_HINTS = [
    (("erp", "crm", "hrms", "saas", "software development", "custom software", "web development", "app development"), "Software Company"),
    (("it services", "it company", "it solutions", "managed it"), "IT Services"),
    (("digital marketing", "seo agency", "seo services", "social media marketing", "ppc"), "Digital Marketing Agency"),
    (("web design", "ui design", "ux design", "branding", "graphic design"), "Design Agency"),
    (("law firm", "attorney", "lawyer", "solicitor", "advocate"), "Law Firm"),
    (("real estate", "realtor", "property", "estate agent"), "Real Estate Agency"),
    (("plumb",), "Plumber"), (("electrician", "electrical contractor"), "Electrician"),
    (("roofing", "roofer"), "Roofing Contractor"), (("construction", "builder", "general contractor"), "General Contractor"),
    (("interior design", "interiors", "modular kitchen"), "Interior Designer"),
    (("cleaning service", "house cleaning", "janitorial"), "Cleaning Service"),
    (("accountant", "accounting", "chartered accountant", "bookkeeping", "tax filing"), "Accounting Firm"),
    (("insurance",), "Insurance Agency"),
    (("manufactur", "machining", "fabrication", "industrial equipment", "autoclave", "pharma machinery"), "Manufacturer"),
    (("restaurant", "dining", "biryani", "pizzeria", "bistro"), "Restaurant"), (("cafe", "coffee"), "Cafe"),
    (("bakery", "cakes"), "Bakery"), (("catering",), "Caterer"),
    (("salon", "hair", "barber"), "Beauty Salon"), (("spa", "massage"), "Day Spa"),
    (("gym", "fitness", "crossfit"), "Gym"), (("yoga",), "Yoga Studio"),
    (("resort", "farm stay"), "Resort"), (("hotel", "homestay", "guest house"), "Hotel"),
    (("dental", "dentist"), "Dental Clinic"), (("clinic", "hospital", "doctor", "physiotherapy"), "Medical Clinic"),
    (("school", "academy", "coaching", "institute", "training", "tutoring"), "Educational Institution"),
    (("wedding", "event planner", "events"), "Event Planner"), (("photograph",), "Photographer"),
    (("car repair", "auto repair", "garage", "car service"), "Auto Repair Shop"),
    (("charity", "ngo", "nonprofit", "non-profit", "foundation"), "Non-Profit Organization"),
    (("online store", "shop now", "add to cart", "ecommerce"), "Online Store"),
]

# Search footprints. {kw} = keyword, {loc} = city/area, {country} = country name.
# A query is skipped if it needs {loc}/{country} and none is known. Ordered by what usually works best.
FOOTPRINTS = {
    "roundups_and_lists": [
        'best {kw} in {loc}',
        'top 10 {kw} {loc}',
        '{kw} in {loc} list',
        'top {kw} in {country}',
        'best {kw} {country} list',
        '{kw} "expert roundup"',
    ],
    "local": [
        '{loc} business directory',
        '{loc} {kw} directory',
        '{loc} startups list',
        '{loc} chamber of commerce members',
        '{loc} business association members',
        '{loc} local news business',
        '"{loc}" {kw} blog',
    ],
    "guest_post": [
        '{kw} "write for us"',
        '{kw} "guest post guidelines"',
        '{kw} "become a contributor"',
        '{kw} "submit a guest post" {country}',
    ],
    "resource_page": [
        '{kw} inurl:resources',
        '{kw} "useful links"',
        '{kw} intitle:"resources" "tools"',
    ],
    "podcasts_and_interviews": [
        '{kw} podcast "be a guest"',
        '{country} founder interview {kw}',
    ],
    # {comp} = a competitor's brand (from competitors=); the best SaaS link targets are "X alternatives" lists
    "competitor_alternatives": [
        '"{comp} alternatives"',
        'best {comp} alternatives',
        '{comp} vs',
        '"alternatives to {comp}"',
        '"{comp}" "competitors"',
    ],
    # {brand} = your brand, {domain} = your domain: pages that mention you without a link -> unlinked_mention email
    "unlinked_mentions": [
        '"{brand}" -site:{domain}',
        '"{brand}" review -site:{domain}',
    ],
    "partners_and_tools": [
        '{kw} "technology partners"',
        '{kw} "partner program"',
        '{kw} "preferred suppliers"',
    ],
    "events_and_education": [
        '{loc} meetup {kw}',
        '{loc} college "industry partner"',
        '{loc} sponsor local event',
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
