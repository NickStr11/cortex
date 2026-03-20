@echo off
chcp 65001 >nul 2>&1
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo ========================================
echo   Claude Code - Session Resume
echo   Project: %CD%
echo ========================================
echo.

if exist "%ROOT%\tools\tg-bridge\main.py" (
  start "" /b cmd /c "cd /d ""%ROOT%\tools\tg-bridge"" && uv run python main.py >nul 2>&1"
  echo   TG Bridge started in background
  echo.
)

claude "Resume session. Read CURRENT_CONTEXT.md. Reconstruct the latest state, summarize what was done, name the active track, blockers if any, and the exact next step."

endlocal
