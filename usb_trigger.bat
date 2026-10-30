
@echo off

:loop

:: Open notepad with the current time
start notepad "Current Time: %time%"

:: Play a ringing sound
( echo Set Sound = CreateObject("SAPI.SpVoice") > sound.vbs )
( echo Sound.Speak "Time is now %time%" >> sound.vbs )
start sound.vbs

:: Wait for 5 minutes (300 seconds)
timeout /t 300 >nul

goto loop
