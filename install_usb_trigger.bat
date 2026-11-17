@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "INSTALL_DIR=%ProgramData%\USB-Security-Tool"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TRIGGER_SOURCE=%~dp0usb_trigger.bat"
set "TRIGGER_DEST=%INSTALL_DIR%\usb_trigger.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\USB Security Status.lnk"
set "LEGACY_SHORTCUT=%USERPROFILE%\Desktop\USB Trigger.lnk"

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

powershell -NoProfile -Command "$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($env:SHORTCUT); $shortcut.TargetPath = $env:ComSpec; $shortcut.Arguments = '/k ""' + $env:TRIGGER_DEST + '""'; $shortcut.WorkingDirectory = $env:INSTALL_DIR; $shortcut.IconLocation = ($env:SystemRoot + '\System32\SHELL32.dll,13'); $shortcut.Save()"
if errorlevel 1 (
  echo The launcher was installed, but the desktop shortcut could not be created.
  exit /b 1
)

echo USB Security status launcher installed successfully.
echo It runs once at sign-in and exits. The desktop shortcut keeps the status window open.
echo Run "%~dp0usb-beveiligen.bat" as Administrator to change settings.
exit /b 0

:uninstall
set "CLEANUP_FAILED=0"
call :removeFile "%STARTUP_DIR%\usb_trigger.bat"
call :removeFile "%SHORTCUT%"
call :removeFile "%LEGACY_SHORTCUT%"
call :removeFile "%TRIGGER_DEST%"
if exist "%INSTALL_DIR%" rmdir "%INSTALL_DIR%" 2>nul
if exist "%INSTALL_DIR%" set "CLEANUP_FAILED=1"
if "%CLEANUP_FAILED%"=="1" (
  echo USB Security status launcher could not be completely removed.
  exit /b 1
)
echo USB Security status launcher removed.
exit /b 0

:removeFile
if not exist "%~1" exit /b 0
del /q "%~1" 2>nul
if exist "%~1" set "CLEANUP_FAILED=1"
exit /b 0
