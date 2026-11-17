@echo off
setlocal EnableExtensions DisableDelayedExpansion
title USB Security Tool

:: Changes to device and AutoPlay policy require elevated rights.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo Requesting administrator privileges...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

:main
cls
echo USB Security Tool
echo =================
echo 1. Toggle USB write protection
echo 2. Toggle AutoPlay/AutoRun protection
echo 3. Enable both protections
echo 4. Start Windows Sandbox
echo 5. Install Toolwiz Time Freeze
echo 6. Exit
echo.
set "choice="
set /p "choice=Enter your choice (1-6): "

if "%choice%"=="1" goto toggleWriteProtection
if "%choice%"=="2" goto toggleAutoPlayProtection
if "%choice%"=="3" goto quickProtect
if "%choice%"=="4" goto startSandbox
if "%choice%"=="5" goto installToolwiz
if "%choice%"=="6" goto end
echo Invalid choice.
pause
goto main

:toggleWriteProtection
call :getWriteProtect
if "%WRITE_PROTECT%"=="1" (
  echo USB write protection is enabled.
  set /p "confirm=Disable it? (Y/N): "
  if /i "%confirm%"=="Y" call :setWriteProtect 0
) else (
  echo USB write protection is disabled.
  set /p "confirm=Enable it? (Y/N): "
  if /i "%confirm%"=="Y" call :setWriteProtect 1
)
echo.
echo Reconnect removable drives after changing this setting.
pause
goto main

:toggleAutoPlayProtection
call :getAutoPlayProtection
if "%AUTOPLAY_PROTECTION%"=="1" (
  echo AutoPlay/AutoRun protection is enabled.
  set /p "confirm=Restore standard Windows AutoPlay behavior? (Y/N): "
  if /i "%confirm%"=="Y" call :setAutoPlayProtection 145
) else (
  echo AutoPlay/AutoRun protection is not fully enabled.
  set /p "confirm=Block AutoPlay and AutoRun for all drive types? (Y/N): "
  if /i "%confirm%"=="Y" call :setAutoPlayProtection 255
)
pause
goto main

:quickProtect
set /p "confirm=Enable USB write protection and block AutoPlay/AutoRun? (Y/N): "
if /i not "%confirm%"=="Y" goto main
call :setWriteProtect 1
call :setAutoPlayProtection 255
echo Both protections have been requested. Reconnect removable drives to apply write protection.
pause
goto main

:startSandbox
dism /online /Get-FeatureInfo /FeatureName:Containers-DisposableClientVM 2>nul | find /i "State : Enabled" >nul
if not errorlevel 1 (
  echo Starting Windows Sandbox...
  start "" WindowsSandbox.exe
  goto sandboxDone
)
echo Windows Sandbox is not enabled or is unavailable on this Windows edition.
set /p "confirm=Enable Windows Sandbox now? A restart will be required. (Y/N): "
if /i "%confirm%"=="Y" (
  dism /online /Enable-Feature /FeatureName:Containers-DisposableClientVM /All /NoRestart
)
:sandboxDone
pause
goto main

:installToolwiz
where winget >nul 2>&1
if errorlevel 1 (
  echo winget is not installed. Install App Installer from Microsoft before continuing.
  pause
  goto main
)
set /p "confirm=Install the third-party Toolwiz Time Freeze package with winget? (Y/N): "
if /i not "%confirm%"=="Y" goto main
winget install --id Toolwiz.TimeFreeze --exact --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
  echo Installation did not complete. Review the winget output above.
) else (
  echo Toolwiz Time Freeze installed successfully.
)
pause
goto main

:getWriteProtect
set "WRITE_PROTECT=0"
for /f "tokens=3" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect 2^>nul ^| find /i "WriteProtect"') do set "WRITE_PROTECT=%%A"
if /i "%WRITE_PROTECT%"=="0x1" set "WRITE_PROTECT=1"
if /i not "%WRITE_PROTECT%"=="1" set "WRITE_PROTECT=0"
exit /b

:setWriteProtect
reg add "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect /t REG_DWORD /d %1 /f >nul
if errorlevel 1 (
  echo Failed to change USB write protection.
  exit /b 1
)
call :getWriteProtect
if "%WRITE_PROTECT%"=="%1" (
  echo USB write protection updated successfully.
) else (
  echo Windows did not report the requested USB write-protection state.
)
exit /b

:getAutoPlayProtection
set "AUTOPLAY_PROTECTION=0"
set "AUTOPLAY_VALUE="
for /f "tokens=3" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun 2^>nul ^| find /i "NoDriveTypeAutoRun"') do set "AUTOPLAY_VALUE=%%A"
if /i "%AUTOPLAY_VALUE%"=="0xff" set "AUTOPLAY_PROTECTION=1"
exit /b

:setAutoPlayProtection
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d %1 /f >nul
if errorlevel 1 (
  echo Failed to change the AutoPlay/AutoRun policy.
  exit /b 1
)
call :getAutoPlayProtection
if "%1"=="255" if "%AUTOPLAY_PROTECTION%"=="1" echo AutoPlay/AutoRun protection enabled successfully.
if "%1"=="145" echo Standard Windows AutoPlay policy applied successfully.
exit /b

:end
endlocal
exit /b
