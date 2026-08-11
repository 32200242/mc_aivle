@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\quick-tunnel\start-public-demo.ps1"
if errorlevel 1 pause

