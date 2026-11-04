# Changelog

## 1.2.0: works for any business, any country, many sites

### Added
- **Projects**: `save_project` / `list_projects`. Each site (yours or a client's) remembers its niche, location, country, keywords and competitors. `scan_site` creates one automatically, and `find_opportunities`, `qualify_prospect` and `build_submission_kit` use it.
- **Countries**: 37 countries with name/code aliases (UK→GB, UAE→AE, USA→US) and region groups (EU, EUROPE, GCC, ANZ, NA, SEA, SOUTH_ASIA). Footprints use `{country}`, and phone numbers format correctly per country (`+44 161 496 0123`, `+1 512 555 0142`, `+49 30 123 4567`).
- **About 135 directories** (was about 50): local directories for the US, CA, UK, IE, AU, NZ, AE, DE, FR, ES, IT and ZA, plus new niches: legal, real estate, trades/home services, healthcare (US), fitness, weddings/events, education, nonprofits and ecommerce.
- **About 90 niche words** mapped to directory tags, and about 40 business categories (dentist, law firm, plumber, real estate agency…).
- `custom.json` for your own directories, footprints, outreach templates and category hints. It's merged with the built-ins and never overwritten by updates.
- `add_custom_directory` (optionally limited to one city) and `add_custom_footprint` tools.

### Changed
- Removed India-only defaults: no default country, no hardcoded "India" in queries, and a generic Accept-Language.
- Kit wording works for any business ("offering…" instead of "builds…", "across the United States").
- Roundup queries read naturally for local services ("best plumber in Manchester", not "top plumber companies").
- `find_opportunities` returns `used` (what it searched with) and `notes` (e.g. "no country set").
- Unknown countries return a clear error instead of silently showing only global sites.


## 1.1.0

Improvements from a real run on a live site.

### Added
- `generate_schema`: ready-to-paste LocalBusiness JSON-LD built from your submission kit (address, phone, email, sameAs, founding date). Missing fields are listed, never invented.
- `list_inclusion` outreach template for "top N companies" roundup pages, which are often the best prospects for local businesses.
- `seo_link_audit` now returns `priority_fixes`, a ranked "fix this first" list.
- `qualify_prospect` follows the prospect's contact/about/write-for-us pages to find a real email, returns `recommended_template` and `how_to_approach`, and accepts `topic_keywords` for relevance scoring.
- `scan_site` flags JavaScript-only (client-rendered) pages and reports how many pages each broken outbound link appears on.
- `scan_codebase` flags routes that differ only by case (`/About` vs `/about`) and inconsistent LinkedIn URLs, and shows which files contain each social link.
- `draft_outreach` takes `hook` (one personal line) and `proof` (real facts) and returns `warnings` and `ready_to_send`.

### Fixed
- The kit was saved as `submission_kit_beforth.md` instead of `submission_kit_beforth.in.md` (the domain ending was treated as a file extension).
- `find_opportunities` stopped a footprint group at its first query without a keyword, so local queries were missing.
- The brand name was used as the business category and as a keyword.
- Placeholder values (`XXXXXXXXXX`, `20XX`, `your full address`) were accepted into the kit. They're now rejected and reported.
- Junk emails (`test@test.com`, `you@company.com`, lockfile author emails like `@izs.me`) were reported as contacts.
- The spam check flagged legitimate directories that mention betting apps in their categories. Spam is now judged by outbound links.
- "Write for us" matched any page containing the word "contribute".
- Bot-blocked social sites (LinkedIn, Instagram…) were reported as broken. They're now listed as `unverified_outbound` unless they return a clean 404.
- Prospects that block bots (403/429) got a low score. They now return `check_manually`.
- `local_press` produced broken grammar ("We recently Top IT…"), and `partner` claimed a working relationship that didn't exist. All templates were rewritten.
- Descriptions were cut mid-word or ended on "for"/"and". Services were badly capitalised ("Erp Crm").
- The tracker allowed duplicate entries for the same directory.
- Footprints were reordered: roundups and local lists first.

## 1.0.0
- Initial release.
