@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ========================================
echo   Claude Code — Session Start
echo   Project: %CD%
echo ========================================
echo.

:: TG Bridge — запускаем в фоне
start "" /b cmd /c "cd /d %~dp0tools\tg-bridge && uv run python main.py >nul 2>&1"
echo   TG Bridge started in background

echo.

claude "Старт сессии. Прочитай DEV_CONTEXT.md и PROJECT_CONTEXT.md. Выведи краткий статус проекта и следующий шаг."
