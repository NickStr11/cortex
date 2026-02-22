#!/bin/bash
# Инициализация нового проекта из шаблона claudeCopy
set -e

TEMPLATE_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_BASE="D:/code/2026"

echo "========================================"
echo "  Claude Code — New Project Init"
echo "========================================"
echo ""

# Название проекта
if [ -n "$1" ]; then
    PROJECT_NAME="$1"
else
    read -p "Название проекта: " PROJECT_NAME
fi

if [ -z "$PROJECT_NAME" ]; then
    echo "ERROR: название проекта обязательно"
    exit 1
fi

# Путь
if [ -n "$2" ]; then
    PROJECT_DIR="$2"
else
    PROJECT_DIR="$DEFAULT_BASE/$PROJECT_NAME"
    read -p "Путь [$PROJECT_DIR]: " CUSTOM_DIR
    if [ -n "$CUSTOM_DIR" ]; then
        PROJECT_DIR="$CUSTOM_DIR"
    fi
fi

if [ -d "$PROJECT_DIR" ]; then
    echo "ERROR: директория $PROJECT_DIR уже существует"
    exit 1
fi

echo ""
echo "Создаю проект: $PROJECT_NAME"
echo "Путь: $PROJECT_DIR"
echo ""

# Копирование шаблона
mkdir -p "$PROJECT_DIR"
rsync -a \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='video_output/' \
    --exclude='__pycache__/' \
    --exclude='.venv/' \
    --exclude='.env' \
    --exclude='init-project.sh' \
    "$TEMPLATE_DIR/" "$PROJECT_DIR/"

# Очистка DEV_CONTEXT.md
cat > "$PROJECT_DIR/DEV_CONTEXT.md" << 'DEVEOF'
# Development Context Log

## Последнее обновление
- Дата: $(date +%Y-%m-%d)

## Текущий статус
- Этап: Инициализация
- Последнее действие: Проект создан из шаблона
- Следующий шаг: Заполнить PROJECT_CONTEXT.md, определить стек

## История изменений

## Технические детали
- Архитектура:
- Ключевые зависимости:
- Интеграции:

## Известные проблемы
- Нет

## Прогресс
- [x] Инициализация из шаблона
- [ ] Заполнить PROJECT_CONTEXT.md
- [ ] Настроить стек
DEVEOF

# Подставить реальную дату
sed -i "s/\$(date +%Y-%m-%d)/$(date +%Y-%m-%d)/" "$PROJECT_DIR/DEV_CONTEXT.md"

# Git init
cd "$PROJECT_DIR"
git init
git add -A
git commit -m "init: project scaffold from claudeCopy template"

echo ""
echo "========================================"
echo "  Проект создан: $PROJECT_NAME"
echo "  Путь: $PROJECT_DIR"
echo "========================================"
echo ""
echo "Следующие шаги:"
echo "  1. cd $PROJECT_DIR"
echo "  2. claude  (или запусти start.bat)"
echo "  3. Заполни PROJECT_CONTEXT.md"
echo ""
