@echo off
chcp 65001 >nul 2>&1
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

claude "Session start. Read CURRENT_CONTEXT.md. Brief status, active track, and next step."

endlocal
