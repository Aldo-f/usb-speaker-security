@echo off
setlocal EnableExtensions
echo usb-beveiligen.bat is a compatibility wrapper. Use usb-security instead. 1>&2
where usb-security >nul 2>&1
if errorlevel 1 goto fallback
usb-security %*
exit /b %errorlevel%

:fallback
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
py -3 -m usb_security.cli %*
exit /b %errorlevel%
