# Ady's Backlinks MCP

An MCP server that lets **Claude** scan a website (or its code) and help build **real backlinks**.
It finds directories to list on, finds sites to pitch, writes the outreach emails, checks links are
live, and tracks everything.

**Works for any business, in any country, and for as many sites as you like:** your own site and
all your clients' sites, each saved as its own project. A dentist in Austin, a plumber in Manchester,
a software company in Nashik and a real estate agency in Dubai each get their own local directories,
search queries, phone format and schema.

> **No spam.** It never auto-posts links (no comment spam, forum spam, PBNs or paid link farms).
> Google penalises those. It finds the right places and prepares everything; you submit and send.

---

## Contents

- [What it can do](#what-it-can-do)
- [Works for any business and country](#works-for-any-business-and-country)
- [Quick install (1 command)](#quick-install-1-command)
- [Manual install](#manual-install)
- [Connect it to your app](#connect-it-to-your-app)
  - [Claude Desktop](#claude-desktop)
  - [Claude Code](#claude-code)
  - [OpenCode / Cursor / other clients](#opencode--cursor--other-clients)
  - [claude.ai web (custom connector)](#claudeai-web-custom-connector)
- [Check it works](#check-it-works)
- [How to use it (copy-paste prompts)](#how-to-use-it-copy-paste-prompts)
- [All tools](#all-tools)
- [Where to add links and text on your pages](#where-to-add-links-and-text-on-your-pages)
- [Multiple sites and clients](#multiple-sites-and-clients)
- [Where your data is saved](#where-your-data-is-saved)
- [Add your own directories and queries](#add-your-own-directories-and-queries)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)

---

## What it can do

```
 Your site / code
       │
       ▼
 1. SCAN      →  business name, phone, address, keywords, pages, broken links
 2. AUDIT     →  a ranked "fix this first" list + ready-to-paste LocalBusiness schema
 3. CONTENT   →  where to add in-text links (exact sentence + file/line) and what paragraphs thin pages need
 4. FIND      →  directories to join + search queries for guest posts & resource pages
 5. QUALIFY   →  scores each prospect 0-100, finds the real contact email, picks the right email template
 6. PREPARE   →  one copy-paste kit (same name/address/phone everywhere) + outreach emails
 7. TRACK     →  todo → submitted → pitched → live
 8. VERIFY    →  is the link really there? follow or nofollow? still live next month?
```

---

## Works for any business and country

**About 135 built-in directories**, picked automatically for the niche and country:

| Type | Examples |
|---|---|
| Every business | Google Business Profile, Bing Places, Apple Business Connect, LinkedIn, Facebook, Trustpilot, Hotfrog |
| Local directories | **US** BBB, Yellow Pages, Manta · **UK** Yell, Thomson Local, FreeIndex · **CA** YellowPages.ca · **AU** Yellow Pages, True Local · **NZ** Finda · **IN** Justdial, Sulekha · **AE** Yellow Pages UAE · **DE** Gelbe Seiten, Das Örtliche · **FR** PagesJaunes · **ES** Páginas Amarillas · **IT** PagineGialle · **ZA** Brabys |
| Software, IT and agencies | Clutch, GoodFirms, DesignRush, G2, Capterra, Product Hunt, GitHub, Wellfound |
| Trades and home services | Checkatrade, TrustATrader (UK) · Angi, Thumbtack (US) · HomeStars (CA) · hipages (AU) · Houzz Pro, Bark |
| Healthcare | Zocdoc, Healthgrades (US) · Practo (IN) · RateMDs |
| Legal | Avvo, Justia, FindLaw (US) · Law Society (UK) · LawRato (IN) |
| Real estate | Zillow, Realtor.com (US) · Rightmove, Zoopla (UK) · realestate.com.au · Bayut, Property Finder (UAE) · 99acres, MagicBricks (IN) |
| Restaurants and food | Tripadvisor, OpenTable, Uber Eats, Yelp, DoorDash, Deliveroo, TheFork, Talabat, Zomato, Swiggy |
| Hotels and stays | Booking.com, Airbnb, MakeMyTrip |
| Beauty and fitness | Fresha, Booksy, Treatwell, Vagaro, Mindbody, ClassPass |
| Manufacturing / B2B | Kompass, Europages, Wer liefert was, Thomasnet, IndiaMART, TradeIndia, Alibaba |
| Education, events, nonprofits | Niche, GreatSchools, The Knot, Hitched, WedMeGood, Candid, GlobalGiving |

**Niches it understands:** software, SaaS, IT, web/app development, marketing/SEO agency, design,
startup, manufacturing, industrial, pharma, wholesale, restaurant, cafe, bakery, catering, salon, spa,
barber, gym, yoga, hotel, resort, travel, clinic, dentist, physio, lawyer/solicitor, real estate,
plumber, electrician, contractor, builder, roofer, cleaner, interior design, architect, HVAC,
landscaping, school, coaching, tutor, online store, wedding, events, photographer, accountant, tax,
insurance, car repair, charity/NGO. Something not on the list still works; you just get general
directories plus anything you add yourself.

**Countries:** India, US, Canada, UK, Ireland, Australia, New Zealand, UAE, Saudi Arabia, Qatar,
Singapore, Malaysia, Philippines, Indonesia, Thailand, Vietnam, Japan, Pakistan, Bangladesh,
Sri Lanka, Nepal, Germany, France, Spain, Italy, Netherlands, Belgium, Switzerland, Sweden, Poland,
Portugal, South Africa, Nigeria, Kenya, Egypt, Brazil and Mexico. You can type names or codes:
`UK`, `GB`, `United Kingdom`, `UAE`, `USA`, `India`, `IN`. Each country gets the right local
directories, search queries, phone format (`+44 161 496 0123`) and schema country code. Adding a
country takes one line in `backlink_mcp/countries.py`.

---

## Quick install (1 command)

You need **Python 3.10 or newer** and **git**.

### macOS / Linux

```bash
git clone https://github.com/RandomKid24/adys-backlinks-mcp.git ~/adys-backlinks-mcp
cd ~/adys-backlinks-mcp
bash install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/RandomKid24/adys-backlinks-mcp.git $HOME\adys-backlinks-mcp
cd $HOME\adys-backlinks-mcp
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer:
1. creates a private Python environment in `.venv` (nothing installed system-wide)
2. installs the server
3. adds it to **Claude Desktop** automatically, backing up your old config as `.bak`
4. adds it to **Claude Code** too, if you have it

Then **fully quit Claude Desktop** (Mac: `Cmd + Q`, Windows: tray icon → Quit), reopen it, and you're done.

> **Mac tip:** keep the folder in your home folder (`~/adys-backlinks-mcp`), **not** in Downloads,
> Desktop or Documents. macOS can block apps from running files there.

---

## Manual install

<details>
<summary>Click to expand</summary>

```bash
git clone https://github.com/RandomKid24/adys-backlinks-mcp.git ~/adys-backlinks-mcp
cd ~/adys-backlinks-mcp

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

which backlink-mcp                 # Windows: where backlink-mcp
```

Copy the path that last command prints. You'll paste it into your app's config below.
It looks like `/Users/you/adys-backlinks-mcp/.venv/bin/backlink-mcp`.

</details>

---

## Connect it to your app

Replace `/FULL/PATH/TO/` with your real path. If you used the installer, it printed this path at the end.

### Claude Desktop

The installer already did this. To do it by hand, open the config file:

| OS | File |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Or open it from Claude Desktop: **Settings → Developer → Edit Config**.

```json
{
  "mcpServers": {
    "backlinks": {
      "command": "/FULL/PATH/TO/adys-backlinks-mcp/.venv/bin/backlink-mcp"
    }
  }
}
```

On Windows the path looks like `C:\\Users\\you\\adys-backlinks-mcp\\.venv\\Scripts\\backlink-mcp.exe`
(use double backslashes).

If you already have other servers, add `"backlinks": {...}` **inside** your existing `mcpServers`
instead of replacing the whole file.

Save the file, fully quit Claude Desktop, and reopen it.

### Claude Code

```bash
claude mcp add backlinks -- /FULL/PATH/TO/adys-backlinks-mcp/.venv/bin/backlink-mcp
```

Inside Claude Code, type `/mcp` and you should see `backlinks · connected`.

### OpenCode / Cursor / other clients

**OpenCode:** add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "backlinks": {
      "type": "local",
      "command": ["/FULL/PATH/TO/adys-backlinks-mcp/.venv/bin/backlink-mcp"],
      "enabled": true
    }
  }
}
```

**Cursor:** add to `~/.cursor/mcp.json`, using the same format as the Claude Desktop JSON above.

Any other MCP client works too: it's a standard **stdio** server. Point it at the `backlink-mcp` path.

### claude.ai web (custom connector)

claude.ai runs in the cloud, so it can't start a program on your computer. It needs a public
`https://` URL. Run the server in HTTP mode and open a free Cloudflare tunnel to it.

**1. Install cloudflared** (one time)

```bash
brew install cloudflared          # Mac
# Windows: winget install Cloudflare.cloudflared
```

**2. Terminal 1: start the server in HTTP mode**

```bash
~/adys-backlinks-mcp/.venv/bin/backlink-mcp --http
```

It prints your secret path, for example:

```
claude.ai connector URL:  https://<your-tunnel-host>/Lvl_-h-kNDN896jX2w7yO5w7TdOQPeXN/mcp
```

**3. Terminal 2: start the tunnel**

```bash
cloudflared tunnel --url http://localhost:8787
```

It prints a URL like `https://random-words.trycloudflare.com`.

**4. Add it on claude.ai**

Go to **Settings → Connectors → Add custom connector**, then:
- Name: `backlinks`
- URL: `https://random-words.trycloudflare.com/<your-secret>/mcp`
- Leave the OAuth fields empty, then click **Add**.

Then turn it on in a chat from the **+ / tools** menu.

**Good to know:**
- Keep **both terminals open** and your computer awake while you use it.
- The `trycloudflare.com` URL **changes every restart**. For a permanent URL, use a
  [named Cloudflare tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
  on your own domain (e.g. `seo-mcp.yourdomain.com`).
- The secret in the URL is the password. **Don't share it.** Make a new one with
  `backlink-mcp --http --new-token`.
- Opening the URL in a browser shows `"Missing session ID"`. That's **normal**: browsers can't
  speak MCP. A wrong secret shows `404` instead.
- Options: `--port 8787` (default), `--host 127.0.0.1` (default). You can also set the secret with
  the `BACKLINK_MCP_TOKEN` environment variable.

---

## Check it works

**Option A: in Claude.** Open a new chat and type:

```
use backlinks to scan https://yoursite.com with max 5 pages
```

You should get your business name, pages and keywords back.

**Option B: MCP Inspector** (needs Node.js; tests the server without Claude)

```bash
npx @modelcontextprotocol/inspector ~/adys-backlinks-mcp/.venv/bin/backlink-mcp
```

Click **Connect**, then **Tools → List Tools**. You should see **19 tools**. Run `scan_site` to test.

**Option C: quick terminal check**

```bash
~/adys-backlinks-mcp/.venv/bin/backlink-mcp
```

If it just sits there waiting, it's working (it's listening for an MCP client). Press `Ctrl + C` to stop.

---

## How to use it (copy-paste prompts)

Send these to Claude **one at a time**, in order. Replace the example values with the real site's
details. Works the same for your own site or a client's.

> **Golden rule:** give Claude **real** details. The tool rejects placeholders like `XXXXXXXXXX`,
> `20XX` or `your full address`, because one wrong phone number copied to 20 directories is worse than none.

**1. Save the site as a project** (once per site)
```
Use backlinks save_project for example.com with niche "dental clinic", location "Austin", country "US", keywords ["dentist", "family dentist", "teeth whitening"], competitors ["competitor1.com", "competitor2.com"].
```
After this, every other tool remembers the niche, city, country and keywords. Just mention the site.

**2. Scan and audit**
```
Use backlinks to scan https://example.com (max 50 pages), then run seo_link_audit and internal_link_suggestions. Show me the priority_fixes list.
```

**3. Connect the code (optional, if you have it)**
```
Use backlinks scan_codebase on /path/to/the/website/code with site example.com and tell me exactly which files to change for each priority fix.
```
Passing `site` remembers the code folder, so the next step can name the exact file and line for every edit.

**3b. Where to add links and text**
```
Use backlinks internal_link_suggestions and content_plan for example.com. For each link, show me the page, section, the sentence with the link added, and the file/line. For thin pages, show which sections and paragraphs to add.
```

**4. Make the submission kit** (real details only)
```
Use backlinks build_submission_kit for example.com with business_name "Example Dental", address "1200 Congress Ave", postal_code "78701", state "TX", email "hello@example.com", phone "(512) 555-0142", founded "2016", services ["Family Dentistry", "Teeth Whitening", "Dental Implants"], description "One or two sentences in your own words.". Show me needs_review.
```
Leave out anything you don't know yet. The kit will list it under `needs_review`. City and country come from the project.

**5. Add business schema to the site**
```
Use backlinks generate_schema for example.com with business_type "Dentist" and add the script tag to the site's <head>.
```
Common types: `ProfessionalService`, `LocalBusiness`, `Dentist`, `Physician`, `LegalService`, `Attorney`,
`RealEstateAgent`, `Plumber`, `Electrician`, `GeneralContractor`, `Restaurant`, `CafeOrCoffeeShop`,
`Bakery`, `BeautySalon`, `HealthClub`, `Hotel`, `Store`, `AutoRepair`, `AccountingService`,
`EducationalOrganization`, `NGO`. The full list is on [schema.org/LocalBusiness](https://schema.org/LocalBusiness).

**6. Find where to get links**
```
Use backlinks find_opportunities for example.com. Give me the top 15 directories to sign up on first, with links.
```
Now sign up on those directories, copy-pasting from the kit. **This is the fastest way to get the first links.**

**7. Find real sites to pitch**
```
Run the roundups_and_lists and local search footprints for example.com with web search. Run qualify_prospect on the top 15 results with my_domain example.com. Add the "good" ones to the tracker. List any "check_manually" ones separately.
```

**8. Write the emails**
```
For each good prospect, use draft_outreach with its recommended_template, my_site example.com, my_name "Your Name", a one-line hook about their page, and proof from these real facts: ["fact 1", "fact 2"]. Show me any warnings.
```
Only put **true** facts in `proof` (customers served, years in business, reviews, awards). Skip
prospects whose template is `signup`: those are just profile sign-ups, no email needed.

**Anytime later**
```
list my backlink projects
show my backlink tracker for example.com
I got listed on https://somesite.com/our-profile, verify it for example.com and mark it live
recheck my live links for example.com          ← do this once a month
```

---

## Where to add links and text on your pages

Links inside your **body text** (the paragraphs on a page) are called **contextual** or
**in-content links**. The clickable words are the **anchor text**. These links pass far more value
than links in the menu or footer. The MCP tells you exactly where to put them, and what text to add
when a page is too short.

**`internal_link_suggestions`: where to put each link**

```json
{
  "placement": "existing_text",
  "add_link_on_page": "https://example.com/",
  "link_to": "https://example.com/product/erp",
  "anchor_text": "manufacturing ERP",
  "section": "What we build",
  "sentence": "We design manufacturing ERP systems that replace messy spreadsheets...",
  "sentence_with_link": "We design <a href=\"/product/erp\">manufacturing ERP</a> systems that replace messy spreadsheets...",
  "code_location": [{"file": "src/pages/Home.tsx", "line": 6}]
}
```

- `existing_text`: the words are already on the page. Just wrap them in a link.
- `add_sentence`: nothing on the page mentions the topic yet. You get a short sentence to add (reword
  it in your own voice) and the paragraph to add it after.
- `code_location`: the file and line to edit. Works with React/JSX (even when text is split across
  lines), Next.js, Vue, Svelte, Astro, HTML, Markdown and Django templates. It needs
  `scan_codebase ... site=example.com` (or `save_project ... code_path=...`) run once.
- Menu and footer links don't count as "already linked", because a link inside the paragraph is stronger.
- It never suggests vague anchors like "click here" or a lone "software", and it adds at most one link per sentence where possible.

**`content_plan`: what paragraphs to add to thin pages**

For each short page, it gives:
- the page type (home, service, contact, about, article, case study, pricing, FAQ…)
- words now vs. the target length
- the **sections to add**, each with what to write in it (e.g. a contact page gets "Contact details",
  "Opening hours", "How to find us", "What happens next" and "Areas we serve")
- keywords to work in naturally (once or twice, never stuffed)
- internal links the new text should include
- where to insert it, and which file to edit

Ask for one page with `content_plan for example.com url /contact`.

---

## Multiple sites and clients

Every site is its own **project**, so one install handles your site and every client's:

```
Use backlinks save_project for client-one.com with niche "law firm", location "Leeds", country "UK"
Use backlinks save_project for client-two.com with niche "restaurant", location "Pune", country "India"
list my backlink projects
```

- `scan_site` creates a project automatically the first time a site is scanned. Run `save_project`
  to add the niche, location and country.
- Each project has its own scan, submission kit, schema and tracker entries.
- `list_projects` shows every site with its tracker progress (todo / submitted / live).
- When working on a client, always mention their domain so the tools use the right project.

---

## All tools

| Tool | What it does |
|---|---|
| `scan_site` | Crawls your live site (follows `robots.txt`, reads `sitemap.xml`). Finds business name, phone, email, address, socials, keywords, page SEO data and broken links. Separates truly broken links from bot-blocked ones (LinkedIn, Instagram…) and flags JavaScript-only pages. |
| `scan_codebase` | (Pass `site=` to remember the folder for that project.) Reads a local project (Next.js, React/Vite, Django, FastAPI, plain HTML…). Finds routes, meta tags, sitemap/robots, structured data, contact info and which file holds each social link. Flags mixed-case routes (`/About` vs `/about`), inconsistent LinkedIn URLs and missing prerendering. Ignores lockfiles and minified bundles. |
| `seo_link_audit` | Returns a ranked `priority_fixes` list (most important first): noindex, broken links (with how many pages each is on), missing LocalBusiness schema / street address, JS-only pages, sitemap, canonicals, thin pages, weak internal links. |
| `internal_link_suggestions` | Says exactly where to add in-text links: page, section, paragraph, sentence, anchor text, the sentence with the link already added, and the **file and line** in your code. If no sentence fits, it suggests a new one and where to put it. |
| `content_plan` | For thin pages: which sections and paragraphs to add, what to write in each, keywords to use naturally, links to include, where to insert them, and which file to edit. |
| `save_project` | Saves a site (yours or a client's) with its niche, location, country, keywords, competitors and code folder, so every other tool uses them. |
| `list_projects` | Lists all your sites with niche, location, country, tracker progress and whether a kit is saved. |
| `find_opportunities` | Lists directories and citation sites for the niche and country, plus ready search queries for roundups, local lists, guest posts, resource pages, podcasts, partners and competitor mentions. Pass `site=` to use a saved project. |
| `add_custom_directory` | Adds your own directory (optionally only for one city). It's saved to `custom.json` and survives updates. |
| `add_custom_footprint` | Adds your own search query using `{kw}`, `{loc}` and `{country}`. |
| `qualify_prospect` | Opens a prospect and scores it 0-100. Detects guest-post pages, "top N companies" roundups, resource pages and directories. Judges spam by where the page links out (not by words in it). Follows contact/about pages to find a real email, and returns `recommended_template`. Blocked sites return `check_manually`, not a bad score. |
| `build_submission_kit` | Builds one consistent Name/Address/Phone + descriptions kit for all directory sign-ups. Rejects placeholder values, never uses your brand name as the category, formats the phone one way, and lists `needs_review`. Saved as `.md` + `.json`. |
| `generate_schema` | Ready-to-paste `LocalBusiness` JSON-LD (address, phone, email, sameAs, founding date) built from your kit. Lists missing fields instead of inventing them. |
| `draft_outreach` | Writes an email: `guest_post`, `list_inclusion`, `resource_page`, `broken_link`, `unlinked_mention`, `partner`, `testimonial`, `local_press`. Uses your personal `hook` and real `proof`, never claims a relationship you don't have, and returns `warnings` until it's ready to send. Never sends anything. |
| `verify_backlink` | Checks a page really links to you: anchor text, follow/nofollow/sponsored, and whether that page is indexable. |
| `tracker_add` | Adds an opportunity to your tracker. Blocks a second entry for the same directory. |
| `tracker_update` | Changes status/notes: `todo`, `submitted`, `pitched`, `live`, `rejected`. |
| `tracker_list` | Shows your tracker with a summary. |
| `recheck_live_links` | Re-checks all your live links and flags any that got removed or became nofollow. |

---

## Where your data is saved

Everything stays on your computer in `~/.backlink-mcp/`:

| File | What |
|---|---|
| `projects.json` | your sites/clients: niche, location, country, keywords, competitors |
| `custom.json` | your own directories, search queries, email templates and categories |
| `tracker.json` | your opportunities and their status (for all sites) |
| `submission_kit_<domain>.md` / `.json` | your copy-paste kit |
| `scans/<domain>.json` | the last scan (used by audit and link suggestions) |
| `http_token` | the secret for HTTP mode |

To use a different folder, set the `BACKLINK_MCP_DATA` environment variable.

Open the folder:
```bash
open ~/.backlink-mcp        # Mac
explorer %USERPROFILE%\.backlink-mcp   # Windows
```

---

## Add your own directories and queries

Your additions go in `~/.backlink-mcp/custom.json`, **not** in the code, so `git pull` never overwrites them.

**The easy way: ask Claude**
```
Use backlinks add_custom_directory "Leeds Chamber of Commerce", url https://www.leedschamber.co.uk/, tags ["general", "local"], region "UK", priority 5, location "Leeds"
Use backlinks add_custom_footprint group "local", query "{loc} {kw} association members"
```

**By hand: edit `custom.json`**
```json
{
  "directories": [
    {"name": "Leeds Chamber of Commerce", "url": "https://www.leedschamber.co.uk/",
     "tags": ["general", "local"], "region": "GB", "priority": 5, "location": "Leeds",
     "notes": "members get a listing"}
  ],
  "footprints": {
    "local": ["{loc} {kw} association members"]
  },
  "outreach_templates": {
    "sponsorship": {
      "needs": ["topic"],
      "subject": "Sponsoring {topic}",
      "body": "Hi {contact},\n\n{hook}\n\nWe'd love to sponsor {topic}...\n\n{my_name}\n{my_site}"
    }
  },
  "category_hints": [
    [["drone", "aerial"], "Aerial Photography Service"]
  ]
}
```

| Field | Meaning |
|---|---|
| `region` | `global`, a country code (`US`, `GB`, `IN`…) or a region: `EU`, `EUROPE`, `GCC`, `ANZ`, `NA`, `SEA`, `SOUTH_ASIA`. Can be a list. |
| `location` | optional; only shown for projects in this city or area |
| `tags` | the niches it suits: `general`, `local`, `software`, `it`, `saas`, `agency`, `design`, `startup`, `manufacturing`, `b2b`, `food`, `hospitality`, `beauty`, `fitness`, `healthcare`, `legal`, `realestate`, `trades`, `education`, `ecommerce`, `events`, `finance`, `automotive`, `nonprofit` |
| `priority` | 5 = do first … 1 = nice to have |
| Footprint placeholders | `{kw}` keyword, `{loc}` city/area, `{country}` country name |
| Template placeholders | `{contact}` `{target_site}` `{topic}` `{hook}` `{proof}` `{my_site}` `{my_name}` `{my_page}` `{broken_url}` |

Your entries win over built-ins with the same name. To change the built-in lists for everyone
(for example, in a pull request), edit `backlink_mcp/data.py` and `backlink_mcp/countries.py`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `spawn ... ENOENT` | The path in your config is wrong. Run `which backlink-mcp` (inside the venv) and paste that exact path. |
| `Remote connect failed` on claude.ai | claude.ai can't run local paths. Use the [HTTP + tunnel setup](#claudeai-web-custom-connector), or use Claude Desktop. |
| `externally-managed-environment` | You ran `pip install` outside the venv. Use `bash install.sh`, or run `source .venv/bin/activate` first. |
| `Operation not permitted` (Mac) | The folder is in Downloads/Desktop/Documents. Move it to `~/adys-backlinks-mcp`, delete `.venv`, and run `bash install.sh` again. |
| Tools don't appear in Claude Desktop | Fully quit it (`Cmd + Q` / tray → Quit), not just close the window. Check the JSON is valid. |
| `"Missing session ID"` in the browser | Normal. Browsers can't speak MCP. Add the URL in claude.ai instead. |
| `404` on the HTTP URL | Wrong secret in the URL. Copy it again from the `--http` startup message. |
| SSL certificate error during scans (Mac) | Run `/Applications/Python\ 3*/Install\ Certificates.command` |
| Scan finds 0 pages | The site blocks bots or is client-side only. Use `scan_codebase` on the project folder instead. |
| Prospect says `check_manually` | That site blocks bots. It's not a bad site. Open it yourself or ask Claude to read it with web fetch. |
| `internal_link_suggestions` says "older version" | Run `scan_site` again. Paragraph data was added in 1.3.0. |
| No `code_location` in suggestions | Run `scan_codebase` with `site=` once, or `save_project` with `code_path=`. If it's still empty, that text comes from a CMS or database, not the code. |
| `find_opportunities` shows only general sites | No country was set, or the niche word wasn't recognised. Run `save_project` with a country and a common niche word (e.g. "dentist"), or add your own with `add_custom_directory`. |
| `Unknown country` | Use a name or code: `India`/`IN`, `UK`/`GB`, `US`/`USA`, `UAE`/`AE`, `Australia`/`AU`… |
| Kit says `ready_to_submit: false` | Look at `needs_review`. Usually a missing street address or PIN code. |
| `command not found: backlink-mcp` | The venv isn't active. Use the full path: `~/adys-backlinks-mcp/.venv/bin/backlink-mcp` |

**Logs**

- Mac: `tail -50 ~/Library/Logs/Claude/mcp-server-backlinks.log`
- Windows: `%APPDATA%\Claude\logs\mcp-server-backlinks.log`

---

## Update

See [CHANGELOG.md](CHANGELOG.md) for what changed.


```bash
cd ~/adys-backlinks-mcp
git pull
.venv/bin/pip install -e .         # Windows: .venv\Scripts\pip install -e .
```

Then restart Claude.

## Uninstall

1. Remove the `"backlinks"` block from your Claude Desktop config (and run `claude mcp remove backlinks` for Claude Code).
2. Delete the folder: `rm -rf ~/adys-backlinks-mcp`
3. (Optional) delete your data: `rm -rf ~/.backlink-mcp`

---

## Requirements

- Python 3.10+
- Works with the `mcp` Python SDK 1.x and 2.x
- macOS, Windows, Linux

## License

MIT. See [LICENSE](LICENSE).
