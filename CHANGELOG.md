# Changelog

## 2.0.0: the full toolkit

### Added
- **JavaScript rendering.** `scan_site` detects React/Vite/Vue shells and crawls them with a headless browser (optional Playwright extra, `render="auto"|"always"|"never"`). `verify_backlink` also renders JS pages, so links injected by JavaScript are found.
- **Much deeper audit, with a health score (0–100, A–F).** New checks: dead buttons/links with no destination (e.g. "Book a Demo" with no href), template placeholders left in titles/OG/Twitter tags ("Vite + React", `@yourtwitterhandle`), sitemap health (entries that 404, redirect or are blocked by robots, and pages missing from the sitemap), robots-blocked links, redirects, canonicals pointing elsewhere, hreflang (missing self/x-default/return links), http links to your own sites, one-page sites, duplicate titles/descriptions, missing alt text, subdomain cross-linking, and the right schema type for products vs local businesses.
- **Sitemap discovery** follows `Sitemap:` lines in robots.txt and sitemap indexes.
- **SaaS/product schema:** `generate_schema` supports `SoftwareApplication`/`WebApplication`/`MobileApplication` with pricing plans (currency from the country), plus a linked `Organization`, optional `FAQPage` and real ratings.
- **New opportunity types:** "competitor alternatives" queries (`"Formspree alternatives"`, `best X alternatives`, `X vs`) and unlinked brand mentions (`"Brand" -site:domain`).
- **About 15 new launch, SaaS, dev and AI directories** (Indie Hackers, Show HN, DevHunt, Uneed, Peerlist, StackShare, SourceForge, Slant, npm, PyPI, Futurepedia, There's An AI For That, Toolify, SoftwareSuggest, Techjockey) and new niches (AI, API/SDK, CMS, no-code, dentist, vet, pharmacy…).
- `link_profile`: follow/nofollow mix, anchor-text mix (branded / URL / exact / partial / generic) and over-optimisation warnings.
- `next_actions`: a daily to-do list across all projects.
- `export_report`: a client-ready, self-contained HTML report (light/dark, mobile-friendly).
- `domain_authority` and authority-aware `qualify_prospect` via an optional free Open PageRank key.
- **Tracker:** automatic follow-up dates, a `followed_up` counter (two unanswered follow-ups → `cold`), and `lost` status when a live link disappears; verified anchor/rel details are stored.
- **Test suite** (29 tests, local fixtures, no internet) and **GitHub Actions CI** on Python 3.10–3.13 × MCP SDK 1.x/2.x, Linux/macOS/Windows, plus a real-browser job.
- The installers ask whether to add JS rendering (`--render` / `--no-render`).

### Changed
- Fix messages show short paths instead of full URL lists.
- Niche matching prefers the longest phrase ("home builder" is trades, "form builder" is software), and agency directories are no longer suggested for SaaS products.
- Branded-anchor detection uses the full brand name or domain, not word fragments.
- The server reports its own version (2.0.0) to MCP clients.


## 1.3.0: where to add links and text

### Added
- `internal_link_suggestions` now says exactly **where** each in-content link goes: the page, section heading, paragraph, sentence, anchor text, a ready `sentence_with_link`, and the **file and line** in your code. When no sentence fits, it proposes a new one (`placement: "add_sentence"`) and the paragraph to add it after.
- `content_plan` tool: for thin pages, the sections and paragraphs to add (by page type: home, service, contact, about, article, case study, pricing, FAQ, careers), what to write in each, keywords to use naturally, internal links to include, target length, and the file to edit.
- `scan_codebase(site=...)` and `save_project(code_path=...)` remember a project's code folder.
- Scans now store body paragraphs with their section heading (re-run `scan_site` after updating).

### Changed
- Menu/header/footer links no longer count as "already linked". Only links inside body text do.
- Anchors can be short acronyms (ERP, CRM, HRMS). Vague single words ("software", "services", "click here") are never used.
- The homepage is never a link target, at most one new link per sentence where possible, and "add a sentence" is only suggested for service, article, case study and pricing pages.


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
