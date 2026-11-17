@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "INSTALL_DIR=%ProgramData%\USB-Security-Tool"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TRIGGER_SOURCE=%~dp0usb_trigger.bat"
set "TRIGGER_DEST=%INSTALL_DIR%\usb_trigger.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\USB Security Status.lnk"

if /i "%~1"=="/uninstall" goto uninstall

if not exist "%TRIGGER_SOURCE%" (
  echo usb_trigger.bat was not found beside this installer.
  echo Run install_usb_trigger.bat from the extracted repository folder.
  exit /b 1
)

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /y "%TRIGGER_SOURCE%" "%TRIGGER_DEST%" >nul
if errorlevel 1 (
  echo Failed to copy the status launcher.
  exit /b 1
)

copy /y "%TRIGGER_DEST%" "%STARTUP_DIR%\usb_trigger.bat" >nul
if errorlevel 1 (
  echo Failed to add the status launcher to the Startup folder.
  exit /b 1
)

powershell -NoProfile -Command "$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($env:SHORTCUT); $shortcut.TargetPath = $env:TRIGGER_DEST; $shortcut.WorkingDirectory = $env:INSTALL_DIR; $shortcut.IconLocation = ($env:SystemRoot + '\System32\SHELL32.dll,13'); $shortcut.Save()"
if errorlevel 1 (
  echo The launcher was installed, but the desktop shortcut could not be created.
  exit /b 1
)

echo USB Security status launcher installed successfully.
echo It runs once at sign-in and exits. Run "%~dp0usb-beveiligen.bat" as Administrator to change settings.
exit /b 0

:uninstall
del /q "%STARTUP_DIR%\usb_trigger.bat" 2>nul
del /q "%SHORTCUT%" 2>nul
del /q "%USERPROFILE%\Desktop\USB Trigger.lnk" 2>nul
del /q "%TRIGGER_DEST%" 2>nul
rmdir "%INSTALL_DIR%" 2>nul
echo USB Security status launcher removed.
exit /b 0
