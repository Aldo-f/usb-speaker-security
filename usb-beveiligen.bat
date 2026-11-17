@echo off
setlocal EnableExtensions
echo usb-beveiligen.bat is a compatibility wrapper. Use usb-security instead.
where usb-security >nul 2>&1
if not errorlevel 1 (
  usb-security %*
  exit /b %errorlevel%
)
py -3 -m usb_security.cli %*
exit /b %errorlevel%
