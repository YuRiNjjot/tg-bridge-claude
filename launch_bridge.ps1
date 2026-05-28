# Bridge Launcher — запускает bridge_bot из указанной папки, убивая старые процессы.
param(
    [string]$BridgeDir = "D:\claudecode\tg-bridge-claude",
    [switch]$NoMonitor
)

$ErrorActionPreference = "Stop"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "========================================" Cyan
Write-Color "  tg-bridge-claude launcher (v2)" Cyan
Write-Color "========================================" Cyan
Write-Color "Target folder: $BridgeDir" DarkGray

# 1. Проверяем что папка существует и есть bridge_bot.py
$botPath = Join-Path $BridgeDir "bridge_bot.py"
if (-not (Test-Path $botPath)) {
    Write-Color "[ERROR] bridge_bot.py not found in $BridgeDir" Red
    exit 1
}

# 2. Ищем и убиваем старые bridge_bot процессы
Write-Color "[KILL] Looking for old bridge_bot processes..." Yellow
$oldProcs = Get-WmiObject Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -like "*bridge_bot.py*")
}

if ($oldProcs) {
    foreach ($proc in $oldProcs) {
        Write-Color "[KILL] Stopping bridge_bot PID $($proc.ProcessId)" Yellow
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Color "[KILL] PID $($proc.ProcessId) stopped." Green
        } catch {
            Write-Color "[KILL] Failed to stop PID $($proc.ProcessId): $_" Red
        }
    }
} else {
    Write-Color "[KILL] No old bridge_bot processes found." DarkGray
}

# 3. Запускаем bridge_bot через pythonw (detached, без консоли, без окна)
Write-Color "[LAUNCH] Starting bridge_bot.py..." Green
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

# Проверяем что процесс жив
if ($proc -and -not $proc.HasExited) {
    Write-Color "[LAUNCH] bridge_bot started! PID: $($proc.Id)" Green
    # Сохраняем PID в файл
    $pidFile = Join-Path $BridgeDir "bot.pid"
    $proc.Id | Out-File $pidFile -Encoding utf8
    Write-Color "[LAUNCH] PID saved to $pidFile" DarkGray
} else {
    Write-Color "[ERROR] bridge_bot failed to start!" Red
    exit 1
}

# 4. Запускаем poller/monitor в текущем терминале (если не -NoMonitor)
if (-not $NoMonitor) {
    Write-Color ""
    Write-Color "[MONITOR] Starting bridge_poller.py..." Yellow
    Write-Color "[MONITOR] Press Ctrl+C to stop monitor." Yellow
    Write-Color "[MONITOR] bridge_bot will keep running in background." DarkGray
    Write-Color ""

    $pollerPath = Join-Path $BridgeDir "bridge_poller.py"
    if (Test-Path $pollerPath) {
        python $pollerPath
    } else {
        Write-Color "[WARN] bridge_poller.py not found, falling back to bridge_monitor.py" DarkYellow
        $monitorPath = Join-Path $BridgeDir "bridge_monitor.py"
        python $monitorPath
    }
}

Write-Color ""
Write-Color "[DONE] Bridge PID: $($newProc.Id)" Green
