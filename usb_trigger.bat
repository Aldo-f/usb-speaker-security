@echo off
setlocal EnableExtensions DisableDelayedExpansion

:: This launcher runs once and exits. It does not create repeated processes.
set "WRITE_PROTECT=Disabled"
set "AUTOPLAY_PROTECTION=Standard"

for /f "tokens=3" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\StorageDevicePolicies" /v WriteProtect 2^>nul ^| find /i "WriteProtect"') do (
  if /i "%%A"=="0x1" set "WRITE_PROTECT=Enabled"
)
for /f "tokens=3" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v NoDriveTypeAutoRun 2^>nul ^| find /i "NoDriveTypeAutoRun"') do (
  if /i "%%A"=="0xff" set "AUTOPLAY_PROTECTION=Blocked"
)

echo USB Security status
echo USB write protection: %WRITE_PROTECT%
echo AutoPlay/AutoRun protection: %AUTOPLAY_PROTECTION%
echo.
echo Run usb-beveiligen.bat as Administrator to change these settings.
endlocal
exit /b
