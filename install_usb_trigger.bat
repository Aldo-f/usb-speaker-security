@echo off
setlocal EnableExtensions
set "INSTALL_DIR=%ProgramData%\USB-Security-Tool"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%USERPROFILE%\Desktop\USB Security Status.lnk"
set "LEGACY_SHORTCUT=%USERPROFILE%\Desktop\USB Trigger.lnk"

if /i "%~1"=="/uninstall" goto uninstall

echo The startup status launcher is retired.
echo Install the Python CLI and run "usb-security status" when needed.
echo Run "%~nx0 /uninstall" once to remove files from an earlier installation.
exit /b 0

:uninstall
set "failed="
if exist "%STARTUP_DIR%\usb_trigger.bat" (
  del /f /q "%STARTUP_DIR%\usb_trigger.bat" >nul 2>&1
  if exist "%STARTUP_DIR%\usb_trigger.bat" set "failed=1"
)
if exist "%SHORTCUT%" (
  del /f /q "%SHORTCUT%" >nul 2>&1
  if exist "%SHORTCUT%" set "failed=1"
)
if exist "%LEGACY_SHORTCUT%" (
  del /f /q "%LEGACY_SHORTCUT%" >nul 2>&1
  if exist "%LEGACY_SHORTCUT%" set "failed=1"
)
if exist "%INSTALL_DIR%\usb_trigger.bat" (
  del /f /q "%INSTALL_DIR%\usb_trigger.bat" >nul 2>&1
  if exist "%INSTALL_DIR%\usb_trigger.bat" set "failed=1"
)
if exist "%INSTALL_DIR%" (
  rmdir "%INSTALL_DIR%" >nul 2>&1
  if exist "%INSTALL_DIR%" set "failed=1"
)
if defined failed (
  echo Some legacy launcher files could not be removed. Remove them manually.
  exit /b 1
)
echo Legacy startup launcher files have been removed.
exit /b 0
