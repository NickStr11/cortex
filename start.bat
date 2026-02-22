@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ========================================
echo   Claude Code — Session Start
echo   Project: %CD%
echo ========================================
echo.

claude "Старт сессии. Прочитай DEV_CONTEXT.md и PROJECT_CONTEXT.md. Выведи краткий статус проекта и следующий шаг."
