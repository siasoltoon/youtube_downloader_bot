$ErrorActionPreference = "Stop"

Write-Host "=== YouTube Downloader Windows Bootstrap ===" -ForegroundColor Cyan

function Install-WingetPackage {
    param(
        [Parameter(Mandatory=$true)][string]$Id,
        [Parameter(Mandatory=$true)][string]$DisplayName
    )

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required to install $DisplayName automatically."
    }

    Write-Host "Installing $DisplayName..." -ForegroundColor Yellow
    winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install $DisplayName with winget (exit=$LASTEXITCODE)."
    }
}

function Refresh-ProcessPath {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @($machinePath, $userPath) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $env:Path = ($parts -join ";")
}

function Export-CommandDirectoryToGitHubPath {
    param(
        [Parameter(Mandatory=$true)][string]$CommandName
    )

    # GITHUB_PATH affects subsequent GitHub Actions steps. This is necessary
    # because a child PowerShell process cannot modify the parent step's PATH.
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_PATH)) {
        return
    }

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $command) {
        return
    }

    $source = $command.Source
    if ([string]::IsNullOrWhiteSpace($source)) {
        return
    }

    $directory = Split-Path -Parent $source
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        Add-Content -Path $env:GITHUB_PATH -Value $directory
        Write-Host "Exported to future GitHub Actions steps: $directory" -ForegroundColor DarkGray
    }
}

function Ensure-Command {
    param(
        [Parameter(Mandatory=$true)][string]$CommandName,
        [Parameter(Mandatory=$true)][string]$DisplayName,
        [string]$WingetId
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        if (-not $WingetId) {
            throw "$DisplayName was not found."
        }
        Install-WingetPackage -Id $WingetId -DisplayName $DisplayName
        Refresh-ProcessPath
    }

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "$DisplayName is still unavailable after installation. Restart the shell and rerun the bootstrap."
    }

    $command = Get-Command $CommandName
    Write-Host "OK: $DisplayName -> $($command.Source)" -ForegroundColor Green
    Export-CommandDirectoryToGitHubPath -CommandName $CommandName
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
    Install-WingetPackage -Id "Python.Python.3.13" -DisplayName "Python 3.13"
    Refresh-ProcessPath
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCommand = "py -3.13"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCommand = "python"
    } else {
        throw "Python 3.13 was installed but is not available in this shell."
    }
}

# Required native tools used by downloader.py.
Ensure-Command -CommandName "ffmpeg" -DisplayName "FFmpeg" -WingetId "Gyan.FFmpeg"
Ensure-Command -CommandName "node" -DisplayName "Node.js 24" -WingetId "OpenJS.NodeJS.LTS"
Ensure-Command -CommandName "git" -DisplayName "Git" -WingetId "Git.Git"

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
