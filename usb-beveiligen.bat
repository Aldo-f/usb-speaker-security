@echo off

:main

:: Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

:: Main menu
echo USB Security Tool
echo ================
echo 1. Toggle USB Write-Protection (Read-Only)
echo 2. Toggle Autoplay / Autorun
echo 3. Quick Protect (Enable both protections)
echo 4. Start Windows Sandbox
echo 5. Install Toolwiz Time Freeze
echo 6. Exit

set /p choice=Enter your choice (1-6):

if "%choice%"=="1" goto toggleWriteProtection
if "%choice%"=="2" goto toggleAutoplay
if "%choice%"=="3" goto quickProtect
if "%choice%"=="4" goto startSandbox
if "%choice%"=="5" goto installToolwiz
echo Invalid choice. Please try again.
goto main

:toggleWriteProtection
:: Check current state and toggle
reg query "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect >nul 2>&1
if %errorLevel% equ 0 (
    reg query "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect | find "0x1" >nul
    if %errorLevel% equ 0 (
        echo Current state: Enabled
        set /p confirm=Disable USB Write-Protection? (Y/N):
        if /i "%confirm%"=="Y" (
            reg add "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect /t REG_DWORD /d 0 /f
            echo USB Write-Protection disabled.
        )
    ) else (
        echo Current state: Disabled
        set /p confirm=Enable USB Write-Protection? (Y/N):
        if /i "%confirm%"=="Y" (
            reg add "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect /t REG_DWORD /d 1 /f
            echo USB Write-Protection enabled.
        )
    )
) else (
    echo Current state: Disabled
    set /p confirm=Enable USB Write-Protection? (Y/N):
    if /i "%confirm%"=="Y" (
        reg add "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect /t REG_DWORD /d 1 /f
        echo USB Write-Protection enabled.
    )
)

pause
goto main

:toggleAutoplay
:: Check current state and toggle
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun >nul 2>&1
if %errorLevel% equ 0 (
    reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun | find "0xff" >nul
    if %errorLevel% equ 0 (
        echo Current state: Enabled
        set /p confirm=Disable Autoplay? (Y/N):
        if /i "%confirm%"=="Y" (
            reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /f
            echo Autoplay disabled.
        )
    ) else (
        echo Current state: Disabled
        set /p confirm=Enable Autoplay? (Y/N):
        if /i "%confirm%"=="Y" (
            reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
            echo Autoplay enabled.
        )
    )
) else (
    echo Current state: Disabled
    set /p confirm=Enable Autoplay? (Y/N):
    if /i "%confirm%"=="Y" (
        reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
        echo Autoplay enabled.
    )
)

pause
goto main

:quickProtect
:: Enable both protections
reg add "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect /t REG_DWORD /d 1 /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f
echo Both protections enabled.
pause
goto main

:startSandbox
:: Check if Windows Sandbox is available and start it
where WindowsSandbox.exe >nul 2>&1
if %errorLevel% equ 0 (
    echo Starting Windows Sandbox...
    WindowsSandbox.exe
) else (
    echo Windows Sandbox is not available on this system.
    set /p confirm=Would you like to enable Windows Sandbox? (Y/N):
    if /i "%confirm%"=="Y" (
        echo Enabling Windows Sandbox...
        dism /online /Enable-Feature /FeatureName:Containers-DisposableClientVM /LimitAccess /ALL
        echo Windows Sandbox has been enabled. Please restart your computer to use it.
    )
)

pause
goto main

:installToolwiz
:: Install Toolwiz Time Freeze
winget install Toolwiz.TimeFreeze
pause
goto main