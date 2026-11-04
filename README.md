# Ady's Backlinks MCP

An MCP server that lets **Claude** scan your website (or its code) and help you build **real backlinks**.
It finds directories to list on, finds sites to pitch, writes your outreach emails, checks your links
are live, and tracks everything.

> **No spam.** It never auto-posts links (no comment spam, forum spam, PBNs or paid link farms).
> Google penalises those. It finds the right places and prepares everything; you submit and send.

---

## Contents

- [What it can do](#what-it-can-do)
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
- [Where your data is saved](#where-your-data-is-saved)
- [Customise](#customise)
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
 3. FIND      →  directories to join + search queries for guest posts & resource pages
 4. QUALIFY   →  scores each prospect 0-100, finds the real contact email, picks the right email template
 5. PREPARE   →  one copy-paste kit (same name/address/phone everywhere) + outreach emails
 6. TRACK     →  todo → submitted → pitched → live
 7. VERIFY    →  is the link really there? follow or nofollow? still live next month?
```

Comes with about 50 curated sites (India + global): Google Business Profile, Bing Places, Justdial,
IndiaMART, Sulekha, TradeIndia, Startup India, Clutch, GoodFirms, DesignRush, G2, Capterra,
Product Hunt, Zomato, Practo, Tripadvisor and more. They're filtered by your niche.

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

Click **Connect**, then **Tools → List Tools**. You should see **14 tools**. Run `scan_site` to test.

**Option C: quick terminal check**

```bash
~/adys-backlinks-mcp/.venv/bin/backlink-mcp
```

If it just sits there waiting, it's working (it's listening for an MCP client). Press `Ctrl + C` to stop.

---

## How to use it (copy-paste prompts)

Send these to Claude **one at a time**, in order. Change `yoursite.com`, the niche, the city and the paths to yours.

> **Golden rule:** give Claude your **real** details. The tool rejects placeholders like `XXXXXXXXXX`,
> `20XX` or `your full address`, because one wrong phone number copied to 20 directories is worse than none.

**1. Scan and audit**
```
Use backlinks to scan https://yoursite.com (max 50 pages), then run seo_link_audit and internal_link_suggestions. Show me the priority_fixes list.
```

**2. Check your code (optional)**
```
Use backlinks scan_codebase on /Users/you/path/to/your-site and tell me exactly which files to change for each priority fix.
```

**3. Make your submission kit** (real details only)
```
Use backlinks build_submission_kit for yoursite.com with business_name "Your Company", city "Your City", state "Your State", postal_code "000000", address "Your street address", email "you@yoursite.com", phone "+91 98xxxxxxxx", founded "2025", services ["Service 1", "Service 2", "Service 3"]. Show me needs_review.
```
Leave out anything you don't know yet. The kit will list it under `needs_review`.

**4. Add business schema to your site**
```
Use backlinks generate_schema for yoursite.com and add the script tag to my site's <head>.
```

**5. Find where to get links**
```
Use backlinks find_opportunities for niche "software erp", location "Your City", country "IN", keywords ["erp software", "custom software development"]. Give me the top 15 directories to sign up on first, with links.
```
Now sign up on those directories, copy-pasting from the kit. **This is the fastest way to get your first links.**

**6. Find real sites to pitch**
```
Run the roundups_and_lists and local search footprints with web search. Run qualify_prospect on the top 15 results with my_domain yoursite.com and topic_keywords ["erp", "software"]. Add the "good" ones to the tracker. List any "check_manually" ones separately.
```

**7. Write the emails**
```
For each good prospect, use draft_outreach with its recommended_template, my_site yoursite.com, my_name YourName, a one-line hook about their page, and proof from these real facts: ["fact 1", "fact 2"]. Show me any warnings.
```
Only put **true** facts in `proof` (clients served, years in business, real results). Skip prospects whose
template is `signup`: those are just profile sign-ups, no email needed.

**Anytime later**
```
show my backlink tracker
I got listed on https://example.com/our-profile, verify it and mark it live
recheck my live links for yoursite.com          ← do this once a month
```

**Niche names that work well:** `software`, `it-services`, `saas`, `erp`, `web design`, `manufacturing`,
`pharma`, `industrial`, `restaurant`, `cafe`, `salon`, `spa`, `hotel`, `resort`, `clinic`, `school`, `startup`.

---

## All tools

| Tool | What it does |
|---|---|
| `scan_site` | Crawls your live site (follows `robots.txt`, reads `sitemap.xml`). Finds business name, phone, email, address, socials, keywords, page SEO data and broken links. Separates truly broken links from bot-blocked ones (LinkedIn, Instagram…) and flags JavaScript-only pages. |
| `scan_codebase` | Reads a local project (Next.js, React/Vite, Django, FastAPI, plain HTML…). Finds routes, meta tags, sitemap/robots, structured data, contact info and which file holds each social link. Flags mixed-case routes (`/About` vs `/about`), inconsistent LinkedIn URLs and missing prerendering. Ignores lockfiles and minified bundles. |
| `seo_link_audit` | Returns a ranked `priority_fixes` list (most important first): noindex, broken links (with how many pages each is on), missing LocalBusiness schema / street address, JS-only pages, sitemap, canonicals, thin pages, weak internal links. |
| `internal_link_suggestions` | Suggests "link from page A to page B with this anchor text" for weakly linked pages. Prefers descriptive multi-word anchors and your strongest pages as sources. |
| `find_opportunities` | Lists directories/citation sites for your niche and country, plus ready search queries for guest posts, resource pages, local lists, podcasts and partners. |
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
| `tracker.json` | your opportunities and their status |
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

## Customise

Edit `backlink_mcp/data.py`:

- **`DIRECTORIES`**: add sites for your niche (`priority` 5 = do first; `region` = `"global"` or a country code like `"IN"`).
- **`FOOTPRINTS`**: add search queries (`{kw}` = keyword, `{loc}` = location).
- **`OUTREACH_TEMPLATES`**: change the email wording. Placeholders: `{contact}` `{target_site}` `{topic}` `{hook}` `{proof}` `{my_site}` `{my_name}` `{my_page}` `{broken_url}`.

Because it's installed with `-e` (editable), changes apply after restarting Claude. No reinstall needed.

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
