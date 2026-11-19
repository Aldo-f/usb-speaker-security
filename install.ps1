<#
.SYNOPSIS
    One-click installer for usb-security on Windows (PowerShell 5.1 or later).
.DESCRIPTION
    Installs the usb-security package for the current user with
    `python -m pip install --user`. Requires Python 3.11+ with pip. Nothing is
    written outside the user's Python environment or the shell; no elevation
    is needed.
.EXAMPLE
    iwr -useb https://raw.githubusercontent.com/Aldo-f/usb-speaker-security/main/install.ps1 | iex
#>

$ErrorActionPreference = 'Stop'
$repoZip = 'https://github.com/Aldo-f/usb-speaker-security/archive/refs/heads/main.zip'
$minimumMajor = 3
$minimumMinor = 11

function Fail([string]$Message) {
    $host.ui.WriteErrorLine("Error: $Message")
    exit 1
}

if ([System.Environment]::OSVersion.Version.Major -lt 10) {
    Fail 'usb-security supports Windows 10 or newer.'
}

$python = $null
foreach ($candidate in @('python', 'python3')) {
    $info = Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $info) {
        continue
    }
    $versionOutput = ''
    try {
        $versionOutput = (& $info.Source --version 2>&1 | Out-String)
    } catch {
        $versionOutput = ''
    }
    if ($versionOutput -match 'Python\s+(\d+)\.(\d+)') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt $minimumMajor -or ($major -eq $minimumMajor -and $minor -ge $minimumMinor)) {
            $python = $info
            break
        }
    }
}
if ($null -eq $python) {
    Fail "usb-security requires Python $minimumMajor.$minimumMinor or newer with pip. Install Python from https://www.python.org/downloads/ and re-run this script."
}

$pipOk = $false
try {
    $pipOutput = (& $python.Source -m pip --version 2>&1)
    $pipOk = ($LASTEXITCODE -eq 0)
} catch {
    $pipOk = $false
}
if (-not $pipOk) {
    Fail "pip is not available for the Python found at $($python.Source). Install pip or reinstall Python from https://www.python.org/downloads/ and re-run this script."
}

Write-Output "Installing usb-security (requires network)..."
try {
    & $python.Source -m pip install --user $repoZip
} catch {
    & $python.Source -m pip install $repoZip
}

Write-Output 'usb-security installed.'
Write-Output 'Run: usb-security status'
if ($null -eq (Get-Command usb-security -ErrorAction SilentlyContinue)) {
    Write-Output "If 'usb-security' is not found, run: $($python.Source) -m usb_security.cli status"
    Write-Output 'or add the user Scripts directory to your PATH and reopen the shell.'
}
