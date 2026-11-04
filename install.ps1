# One-command installer for Windows (PowerShell).
# Run:  powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Dir = (Get-Location).Path

function Say($m)  { Write-Host "==> $m" -ForegroundColor Green }
function Fail($m) { Write-Host "xx  $m" -ForegroundColor Red; exit 1 }

# 1. Python
$Py = $null
foreach ($c in @("py -3", "python", "python3")) {
    try {
        $ok = & cmd /c "$c -c ""import sys; print(sys.version_info >= (3,10))""" 2>$null
        if ($ok -eq "True") { $Py = $c; break }
    } catch {}
}
if (-not $Py) { Fail "Python 3.10+ not found. Install from https://www.python.org/downloads/ (tick 'Add to PATH')." }
Say "Using $(cmd /c "$Py --version")"

# 2. Virtual env + install
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Say "Creating virtual environment (.venv)"
    cmd /c "$Py -m venv .venv"
}
Say "Installing backlink-mcp and dependencies"
& .venv\Scripts\python.exe -m pip install -q --upgrade pip
& .venv\Scripts\python.exe -m pip install -q -e .
$Bin = Join-Path $Dir ".venv\Scripts\backlink-mcp.exe"
if (-not (Test-Path $Bin)) { Fail "Install failed: $Bin not found" }
Say "Installed: $Bin"

# 3. Claude Desktop config
$Cfg = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
& .venv\Scripts\python.exe -c @"
import json, pathlib, shutil, sys
cfg, binp = pathlib.Path(sys.argv[1]), sys.argv[2]
cfg.parent.mkdir(parents=True, exist_ok=True)
data = {}
if cfg.exists() and cfg.read_text().strip():
    shutil.copy(cfg, str(cfg) + '.bak')
    data = json.loads(cfg.read_text())
data.setdefault('mcpServers', {})['backlinks'] = {'command': binp}
cfg.write_text(json.dumps(data, indent=2))
print(f'    added backlinks to {cfg}')
"@ $Cfg $Bin
Say "Claude Desktop configured"

if (Get-Command claude -ErrorAction SilentlyContinue) {
    try { claude mcp add backlinks -- "$Bin" | Out-Null; Say "Claude Code configured" } catch {}
}

Write-Host ""
Say "Done! Next:"
Write-Host "    1. Quit Claude Desktop completely (right-click the tray icon > Quit) and open it again"
Write-Host "    2. In a chat, type:  use backlinks to scan https://yoursite.com with max 5 pages"
Write-Host ""
Write-Host "    Path to use in other MCP clients:  $Bin"
