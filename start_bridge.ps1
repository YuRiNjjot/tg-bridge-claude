# Запуск tg-bridge: bridge_bot (фон) + bridge_monitor (терминал)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  tg-bridge-claude launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Запуск bridge_bot.py в фоне (скрытое окно)
Write-Host "[LAUNCH] Starting bridge_bot.py in background..." -ForegroundColor Green
$bridgeBot = Start-Process -FilePath "python" -ArgumentList "bridge_bot.py" `
    -WindowStyle Hidden -PassThru -WorkingDirectory $Root

Write-Host "[LAUNCH] bridge_bot PID: $($bridgeBot.Id)" -ForegroundColor Green

# 2. Запуск bridge_monitor.py в текущем терминале
Write-Host "[LAUNCH] Starting bridge_monitor.py in terminal..." -ForegroundColor Yellow
Write-Host "[LAUNCH] Press Ctrl+C to stop both." -ForegroundColor Yellow
Write-Host ""

try {
    python bridge_monitor.py
} finally {
    # При остановке monitor — убить bridge_bot
    Write-Host "`n[STOP] Stopping bridge_bot (PID: $($bridgeBot.Id))..." -ForegroundColor Red
    Stop-Process -Id $bridgeBot.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[STOP] Done." -ForegroundColor Red
}
