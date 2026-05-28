# Setup whisper.cpp model for tg-bridge-claude
# Downloads ggml-small.bin if not present

$ErrorActionPreference = "Stop"

$RepoDir = $PSScriptRoot
$ModelDir = Join-Path $RepoDir "models"
$ModelFile = Join-Path $ModelDir "ggml-small.bin"
$ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"

function Write-Color($Text, $Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

Write-Color "[WHISPER SETUP] Checking model..." Cyan

if (Test-Path $ModelFile) {
    $size = (Get-Item $ModelFile).Length / 1MB
    Write-Color "[OK] Model already exists: $ModelFile ({0:N1} MB)" -f $size Green
    exit 0
}

Write-Color "[DOWNLOAD] ggml-small.bin (~466 MB) from HuggingFace..." Yellow
Write-Color "[DOWNLOAD] This may take 2-5 minutes depending on connection..." DarkGray

New-Item -ItemType Directory -Path $ModelDir -Force | Out-Null

try {
    $progressPreference = 'Continue'
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile -UseBasicParsing
    $size = (Get-Item $ModelFile).Length / 1MB
    Write-Color "[OK] Model downloaded: $ModelFile ({0:N1} MB)" -f $size Green
} catch {
    Write-Color "[ERROR] Failed to download model: $_" Red
    if (Test-Path $ModelFile) { Remove-Item $ModelFile -Force }
    exit 1
}
