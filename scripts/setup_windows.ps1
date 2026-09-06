$ErrorActionPreference = "Stop"

Write-Host "=== YouTube Downloader Windows Bootstrap ===" -ForegroundColor Cyan

function Ensure-Command {
    param(
        [Parameter(Mandatory=$true)][string]$CommandName,
        [Parameter(Mandatory=$true)][string]$DisplayName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "$DisplayName was not found. Install it first, then rerun this script."
    }

    $command = Get-Command $CommandName
    Write-Host "OK: $DisplayName -> $($command.Source)" -ForegroundColor Green
}

# Python: prefer the Windows Python launcher when available.
$pythonCommand = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3.13 --version | Out-Host
        if ($LASTEXITCODE -eq 0) {
            $pythonCommand = "py -3.13"
        }
    } catch {}
}

if (-not $pythonCommand -and (Get-Command python -ErrorAction SilentlyContinue)) {
    & python --version | Out-Host
    $pythonCommand = "python"
}

if (-not $pythonCommand) {
    throw "Python 3.13 (or a compatible Python installation) was not found."
}

# Required native tools used by downloader.py.
Ensure-Command -CommandName "ffmpeg" -DisplayName "FFmpeg"
Ensure-Command -CommandName "node" -DisplayName "Node.js"
Ensure-Command -CommandName "git" -DisplayName "Git"

Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
if ($pythonCommand -eq "py -3.13") {
    & py -3.13 -m pip install --upgrade pip
    & py -3.13 -m pip install -r requirements.txt
} else {
    & python -m pip install --upgrade pip
    & python -m pip install -r requirements.txt
}

if ($LASTEXITCODE -ne 0) {
    throw "pip dependency installation failed."
}

Write-Host "`nRunning application health check..." -ForegroundColor Yellow
if ($pythonCommand -eq "py -3.13") {
    & py -3.13 scripts/healthcheck.py
} else {
    & python scripts/healthcheck.py
}

if ($LASTEXITCODE -ne 0) {
    throw "Health check failed."
}

Write-Host "`nBootstrap completed successfully." -ForegroundColor Green
Write-Host "Start the bot with: python bot.py" -ForegroundColor Cyan
