<#
.SYNOPSIS
    One-click installer for usb-security on Windows (PowerShell 5.1 or later).
.DESCRIPTION
    Installs the usb-security package for the current user with
    `python -m pip install --user`. Requires Python 3.11+ with pip. Nothing is
    written outside the user's Python environment or user PATH; no elevation
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

function Set-UserPath([string]$PathValue) {
    $environmentKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Environment')
    if ($null -eq $environmentKey) {
        Fail 'Could not open the current user environment settings to update PATH.'
    }

    try {
        $valueKind = [Microsoft.Win32.RegistryValueKind]::String
        if ($environmentKey.GetValueNames() -contains 'Path') {
            $valueKind = $environmentKey.GetValueKind('Path')
        }
        $environmentKey.SetValue('Path', $PathValue, $valueKind)
    } finally {
        $environmentKey.Dispose()
    }

    if (-not ('UsbSecurityEnvironmentNotifier' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class UsbSecurityEnvironmentNotifier {
    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern IntPtr SendMessageTimeout(
        IntPtr hWnd, uint message, UIntPtr wParam, string lParam,
        uint flags, uint timeout, out UIntPtr result);
}
'@
    }
    $broadcastResult = [UIntPtr]::Zero
    [void][UsbSecurityEnvironmentNotifier]::SendMessageTimeout(
        [IntPtr]::new(65535), 0x001A, [UIntPtr]::Zero,
        'Environment', 0x0002, 1000, [ref]$broadcastResult
    )
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

# Add the user scripts directory to PATH (session + permanently) so the
# `usb-security` command is immediately usable after the install.
$userScriptsDir = (& $python.Source -c "import sysconfig; print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))" 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $userScriptsDir) {
    Fail "Could not determine the Python user Scripts directory. Run: $($python.Source) -m usb_security.cli status"
}
if (-not (Test-Path $userScriptsDir)) {
    Fail "Python reported a user Scripts directory that does not exist: $userScriptsDir"
}
$pathEntries = @($env:PATH -split ';' | Where-Object { $_ })
if (-not ($pathEntries | Where-Object { $_.TrimEnd('\') -ieq $userScriptsDir.TrimEnd('\') })) {
    $env:PATH = "$userScriptsDir;$env:PATH"
}
$userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
$userEntries = @()
if ($userPath) { $userEntries = @($userPath -split ';' | Where-Object { $_ }) }
if (-not ($userEntries | Where-Object { $_.TrimEnd('\') -ieq $userScriptsDir.TrimEnd('\') })) {
    $userEntries += $userScriptsDir
    Set-UserPath ($userEntries -join ';')
    Write-Output "Added $userScriptsDir to the user PATH permanently."
}

Write-Output 'usb-security installed.'
Write-Output 'Run: usb-security status'
if ($null -eq (Get-Command usb-security -ErrorAction SilentlyContinue)) {
    Write-Output "If 'usb-security' is not found, run: $($python.Source) -m usb_security.cli status"
    Write-Output "To make 'usb-security' permanently available, add this directory to your PATH:"
    Write-Output "  $userScriptsDir"
    Write-Output 'In PowerShell, you can run:'
    Write-Output "  `$env:PATH += ';$userScriptsDir'"
    Write-Output 'Or add it via System Properties > Environment Variables.'
}
