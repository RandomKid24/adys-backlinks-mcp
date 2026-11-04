# Changelog

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
