# tg-bridge-claude Installer
# One-liner setup for Windows 11 + Claude Code
# Run: .\install.ps1

$ErrorActionPreference = "Stop"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

$BridgeDir = $PSScriptRoot
$SettingsDir = "$env:USERPROFILE\.claude"
$SettingsFile = "$SettingsDir\settings.json"

Write-Color "╔══════════════════════════════════════════════════════╗" Cyan
Write-Color "║  tg-bridge-claude Installer (Windows 11 Native)      ║" Cyan
Write-Color "╚══════════════════════════════════════════════════════╝" Cyan

# 1. Check Python
Write-Color "`n[1/5] Checking Python..." Yellow
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Color "[ERROR] Python not found. Install from python.org first." Red
    exit 1
}
Write-Color "[OK] Python found: $($python.Source)" Green

# 2. Check ffmpeg
Write-Color "`n[2/5] Checking ffmpeg..." Yellow
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Color "[WARN] ffmpeg not found. Install: winget install ffmpeg" DarkYellow
} else {
    Write-Color "[OK] ffmpeg found" Green
}

# 3. Install Python deps
Write-Color "`n[3/5] Installing Python dependencies..." Yellow
& python -m pip install -r "$BridgeDir\requirements.txt"
Write-Color "[OK] Dependencies installed" Green

# 4. Create .env if missing
Write-Color "`n[4/5] Checking .env configuration..." Yellow
$EnvFile = "$BridgeDir\.env"
if (-not (Test-Path $EnvFile)) {
    Write-Color "[INFO] Creating .env from template..." Cyan
    Copy-Item "$BridgeDir\.env.example" $EnvFile
    Write-Color "[WARN] EDIT .env AND SET YOUR TELEGRAM_BOT_TOKEN!" Yellow
    Write-Color "[WARN] Get token from @BotFather, ADMIN_TG_ID from @userinfobot" Yellow
} else {
    Write-Color "[OK] .env already exists" Green
}

# 5. Auto-approve bridge commands in Claude Code settings
Write-Color "`n[5/5] Configuring Claude Code auto-approve..." Yellow

if (-not (Test-Path $SettingsDir)) {
    New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null
}

$bridgeRules = @(
    "Bash(*bridge_bot.py*)",
    "Bash(*bridge_poller.py*)",
    "Bash(*launch_bridge.ps1*)",
    "Bash(*python*)",
    "PowerShell(*)",
    "Edit(*bridge_outbox.jsonl*)",
    "Write(*bridge_outbox.jsonl*)"
)

if (Test-Path $SettingsFile) {
    $settings = Get-Content $SettingsFile -Raw | ConvertFrom-Json -Depth 10
    if (-not $settings.permissions) {
        $settings | Add-Member -NotePropertyName "permissions" -NotePropertyValue @{defaultMode="auto"; allow=@()} -Force
    }
    if (-not $settings.permissions.allow) {
        $settings.permissions | Add-Member -NotePropertyName "allow" -NotePropertyValue @() -Force
    }
    foreach ($rule in $bridgeRules) {
        if ($settings.permissions.allow -notcontains $rule) {
            $settings.permissions.allow += $rule
            Write-Color "[ADDED] $rule" Green
        }
    }
    $settings | ConvertTo-Json -Depth 10 | Out-File $SettingsFile -Encoding utf8
    Write-Color "[OK] Updated $SettingsFile" Green
} else {
    $settings = @{
        permissions = @{
            defaultMode = "auto"
            allow = $bridgeRules
        }
    }
    $settings | ConvertTo-Json -Depth 10 | Out-File $SettingsFile -Encoding utf8
    Write-Color "[OK] Created $SettingsFile" Green
}

Write-Color "`n═══════════════════════════════════════════════════════" Cyan
Write-Color "  INSTALL COMPLETE!" Green
Write-Color "═══════════════════════════════════════════════════════" Cyan
Write-Color "`nNext steps:" White
Write-Color "  1. EDIT .env file (set TELEGRAM_BOT_TOKEN + ADMIN_TG_ID)" Yellow
Write-Color "  2. Run: .\launch_bridge.ps1" Yellow
Write-Color "  3. Send /start to your bot in Telegram" Yellow
Write-Color "  4. Say 'запустибридж' to Claude Code anytime to restart" Yellow
Write-Color "`nRepo: https://github.com/YuRiNjjot/tg-bridge-claude" DarkGray
