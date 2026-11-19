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

function Find-Python {
    foreach ($candidate in @('python', 'python3')) {
        foreach ($info in (Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue)) {
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
                    return $info
                }
            }
        }
    }
    return $null
}

$python = Find-Python
if ($null -eq $python) {
    $noPythonMessage = "usb-security requires Python $minimumMajor.$minimumMinor or newer with pip. Install Python from https://www.python.org/downloads/ and re-run this script."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail $noPythonMessage
    }
    
    # Find the latest Python 3.x interpreter package in the winget sources.
    $wingetPythonId = $null
    $highestMinor = -1
    $searchResult = winget search --id python --source winget 2>$null
    foreach ($line in ($searchResult -split "`r?`n")) {
        $m = [regex]::Match($line, 'Python\.Python\.3\.(?<minor>\d+)')
        if ($m.Success) {
            $minor = [int]$m.Groups['minor'].Value
            if ($minor -gt $highestMinor) {
                $highestMinor = $minor
                $wingetPythonId = "Python.Python.3.$minor"
            }
        }
    }
    # Fallback to generic package if no versioned packages found
    if (-not $wingetPythonId) {
        winget show --id Python.Python.3 --source winget >$null 2>&1
        if ($LASTEXITCODE -eq 0) { $wingetPythonId = "Python.Python.3" }
    }
    
    if (-not $wingetPythonId) {
        Fail "winget could not find a Python 3.11+ package to install. $noPythonMessage"
    }
    
    $response = Read-Host "No Python $minimumMajor.$minimumMinor or newer was found. Install Python with winget ($wingetPythonId)? [y/N]"
    if ($response -notmatch '^[Yy]') {
        Fail $noPythonMessage
    }
    Write-Output "Installing Python with winget ($wingetPythonId)..."
    winget install --id $wingetPythonId --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Fail "winget failed to install Python $wingetPythonId (exit code $LASTEXITCODE). $noPythonMessage"
    }
    
    # Winget updates the user PATH; merge new user-PATH entries into this session.
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if ($userPath) {
        foreach ($dir in ($userPath -split ';')) {
            if ($dir -and ($dir -notin ($env:PATH -split ';'))) {
                $env:PATH = "$dir;$env:PATH"
            }
        }
    }
    # Also add winget-installed Python directories (user scope) when they contain python.exe.
    foreach ($root in @((Join-Path $env:LOCALAPPDATA 'Programs\Python'), $env:ProgramFiles)) {
        if (-not $root -or -not (Test-Path $root)) {
            continue
        }
        foreach ($pythonDir in (Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue)) {
            $pythonExe = Join-Path $pythonDir.FullName 'python.exe'
            if ((Test-Path $pythonExe) -and ($pythonDir.FullName -notin ($env:PATH -split ';'))) {
                $env:PATH = "$($pythonDir.FullName);$env:PATH"
            }
        }
    }
    $python = Find-Python
    if ($null -eq $python) {
        Fail "Python was installed with winget, but it was not found on this session's PATH. Close and reopen this shell, then re-run this script."
    }
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
