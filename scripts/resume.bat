@echo off
chcp 65001 >nul 2>&1
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

claude "Resume session. Read CURRENT_CONTEXT.md. Reconstruct the latest state, summarize what was done, name the active track, blockers if any, and the exact next step."

endlocal
