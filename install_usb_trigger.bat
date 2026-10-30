
@echo off

:: Copy the USB trigger script to the startup folder
copy usb_trigger.bat "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Create a shortcut to the USB trigger script on the desktop
set SCRIPT="%USERPROFILE%\Desktop\USB Trigger.lnk"
set TARGET="%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\usb_trigger.bat"
set ICON="%SystemRoot%\System32\SHELL32.dll,13"

:: Create the shortcut using PowerShell
powershell -command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut($env:SCRIPT); $Shortcut.TargetPath = $env:TARGET; $Shortcut.IconLocation = $env:ICON; $Shortcut.Save()"

:: Notify the user that the installation is complete
msg * USB Trigger has been installed successfully
