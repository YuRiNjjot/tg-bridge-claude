# Bridge Launcher — запускает bridge_bot + poller.
# ЗАПУСКАТЬ НАПРЯМУЮ В ТЕРМИНАЛЕ: .\launch_bridge.ps1
# НЕ через Claude Code — poller должен работать в foreground.
param(
    [string]$BridgeDir = "D:\claudecode\tg-bridge-claude",
    [switch]$NoMonitor
)

$ErrorActionPreference = "Stop"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "========================================" Cyan
Write-Color "  tg-bridge-claude launcher (v3)" Cyan
Write-Color "========================================" Cyan
Write-Color "Target folder: $BridgeDir" DarkGray

# 1. Убиваем ВСЕ старые bridge-процессы
Write-Color "[KILL] Looking for old bridge processes..." Yellow
$oldProcs = Get-WmiObject Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*bridge_bot.py*" -or
        $_.CommandLine -like "*bridge_poller.py*" -or
        $_.CommandLine -like "*bridge_monitor.py*"
    )
}

if ($oldProcs) {
    foreach ($proc in $oldProcs) {
        Write-Color "[KILL] Stopping PID $($proc.ProcessId) ($($proc.Name))" Yellow
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Color "[KILL] PID $($proc.ProcessId) stopped." Green
        } catch {
            Write-Color "[KILL] Failed: $_" Red
        }
    }
} else {
    Write-Color "[KILL] No old bridge processes found." DarkGray
}

# 2. Запускаем bridge_bot в фоне (pythonw, без консольного окна)
Write-Color "[LAUNCH] Starting bridge_bot.py (background)..." Green
$botPath = Join-Path $BridgeDir "bridge_bot.py"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "pythonw"
$psi.Arguments = "`"$botPath`""
$psi.WorkingDirectory = $BridgeDir
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$proc = [System.Diagnostics.Process]::Start($psi)

Start-Sleep -Seconds 2

if ($proc -and -not $proc.HasExited) {
    Write-Color "[LAUNCH] bridge_bot started! PID: $($proc.Id)" Green
    $proc.Id | Out-File (Join-Path $BridgeDir "bot.pid") -Encoding utf8
} else {
    Write-Color "[ERROR] bridge_bot failed to start!" Red
    exit 1
}

# 3. Запускаем poller в ТЕКУЩЕМ терминале (foreground)
if (-not $NoMonitor) {
    Write-Color ""
    Write-Color "[MONITOR] Starting bridge_poller.py in this terminal..." Yellow
    Write-Color "[MONITOR] Press Ctrl+C to stop monitor." Yellow
    Write-Color "[MONITOR] bridge_bot runs in background." DarkGray
    Write-Color ""

    $pollerPath = Join-Path $BridgeDir "bridge_poller.py"
    if (Test-Path $pollerPath) {
        # ЭТА КОМАНДА БЛОКИРУЕТ ТЕРМИНАЛ — poller работает в foreground
        & python $pollerPath
    } else {
        Write-Color "[WARN] bridge_poller.py not found!" DarkYellow
    }
}

Write-Color ""
Write-Color "[DONE] Exited." Green
