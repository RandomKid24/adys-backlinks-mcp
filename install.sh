#!/usr/bin/env bash
# One-command installer for macOS / Linux.
# Creates a virtual env, installs backlink-mcp, and adds it to Claude Desktop.
set -euo pipefail
# Options:  --render     also install the headless browser for JavaScript sites (React/Vite/Vue)
#           --no-render  skip it without asking
RENDER=""
for a in "$@"; do case "$a" in --render) RENDER=yes ;; --no-render) RENDER=no ;; esac; done

cd "$(dirname "$0")"
DIR="$(pwd)"
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
say()  { printf "${G}==>${N} %s\n" "$*"; }
warn() { printf "${Y}!!${N}  %s\n" "$*"; }
die()  { printf "${R}xx${N}  %s\n" "$*"; exit 1; }

case "$DIR" in
  "$HOME/Downloads"*|"$HOME/Desktop"*|"$HOME/Documents"*)
    [ "$(uname)" = "Darwin" ] && warn "You're inside ~/Downloads, ~/Desktop or ~/Documents. macOS may block Claude Desktop from running files here. Moving the folder to ~/adys-backlinks-mcp first is recommended." ;;
esac

# 1. Python
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
[ -n "$PY" ] || die "Python 3.10+ not found. Install it: brew install python   (Mac)  /  sudo apt install python3 python3-venv   (Linux)"
say "Using $($PY --version)"

# 2. Virtual env + install
if [ ! -x .venv/bin/python ]; then
  say "Creating virtual environment (.venv)"
  "$PY" -m venv .venv
fi
say "Installing backlink-mcp and dependencies"
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -e .
if [ -z "$RENDER" ] && [ -t 0 ]; then
  read -r -p "Install JS rendering for React/Vite/Vue sites? Downloads ~150 MB browser. [y/N] " ans
  case "$ans" in [yY]*) RENDER=yes ;; *) RENDER=no ;; esac
fi
if [ "$RENDER" = "yes" ]; then
  say "Installing JS rendering (Playwright + Chromium)"
  .venv/bin/python -m pip install -q -e ".[render]"
  .venv/bin/python -m playwright install chromium || warn "Chromium download failed - run later: .venv/bin/python -m playwright install chromium"
fi
BIN="$DIR/.venv/bin/backlink-mcp"
[ -x "$BIN" ] || die "Install failed: $BIN not found"
say "Installed: $BIN"

# 3. Claude Desktop config
if [ "$(uname)" = "Darwin" ]; then
  CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
  CFG="${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
fi
.venv/bin/python - "$CFG" "$BIN" <<'EOF'
import json, pathlib, shutil, sys
cfg, binp = pathlib.Path(sys.argv[1]), sys.argv[2]
cfg.parent.mkdir(parents=True, exist_ok=True)
data = {}
if cfg.exists() and cfg.read_text().strip():
    shutil.copy(cfg, str(cfg) + ".bak")
    data = json.loads(cfg.read_text())
data.setdefault("mcpServers", {})["backlinks"] = {"command": binp}
cfg.write_text(json.dumps(data, indent=2))
print(f"    added 'backlinks' to {cfg}")
EOF
say "Claude Desktop configured"

# 4. Claude Code (optional)
if command -v claude >/dev/null 2>&1; then
  claude mcp add backlinks -- "$BIN" >/dev/null 2>&1 && say "Claude Code configured" || warn "Claude Code: already added or failed (run: claude mcp add backlinks -- \"$BIN\")"
fi

echo
say "Done! Next:"
echo "    1. Quit Claude Desktop completely (Cmd+Q) and open it again"
echo "    2. In a chat, type:  use backlinks to scan https://yoursite.com with max 5 pages"
echo
echo "    Path to use in other MCP clients:  $BIN"
