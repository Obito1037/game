@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\Open-JieGuang-V3.ps1" -Web
if errorlevel 1 pause
