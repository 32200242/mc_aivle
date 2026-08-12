@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\quick-tunnel\show-public-demo-url.ps1"
if errorlevel 1 pause
