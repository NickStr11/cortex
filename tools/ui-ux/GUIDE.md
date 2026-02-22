# UI/UX Pro Max - Design Intelligence

AI-инструмент для создания профессионального дизайна. Содержит базу данных стилей,
цветов, шрифтов и UX-гайдлайнов с BM25-поиском.

## Содержимое

| Что | Количество |
|-----|-----------|
| UI стили | 67 (glassmorphism, minimalism, brutalism, etc.) |
| Цветовые палитры | 96 (по индустриям) |
| Font pairings | 57 (с Google Fonts imports) |
| Reasoning rules | 100 (по индустриям) |
| UX guidelines | 99 |
| Chart types | 25 |
| Tech stacks | 13 |

## Использование

### Генерация Design System

При любой дизайн-задаче СНАЧАЛА сгенерируй дизайн-систему:

```bash
python tools/ui-ux/search.py "<product> <industry> <keywords>" --design-system -p "Project Name"
```

**Примеры:**
```bash
# SaaS dashboard
python tools/ui-ux/search.py "saas dashboard analytics" --design-system -p "FinanceApp"

# Beauty landing
python tools/ui-ux/search.py "beauty spa wellness" --design-system -p "Serenity Spa"

# E-commerce
python tools/ui-ux/search.py "ecommerce fashion luxury" --design-system -p "StyleShop"
```

### Поиск по доменам

```bash
# Поиск стилей
python tools/ui-ux/search.py "glassmorphism" --domain style

# Поиск цветов
python tools/ui-ux/search.py "fintech" --domain color

# Поиск шрифтов
python tools/ui-ux/search.py "elegant luxury" --domain typography

# UX guidelines
python tools/ui-ux/search.py "animation accessibility" --domain ux
```

### Stack-specific guidelines

```bash
python tools/ui-ux/search.py "form validation" --stack react
python tools/ui-ux/search.py "responsive layout" --stack html-tailwind
```

**Доступные стеки:** `html-tailwind`, `react`, `nextjs`, `vue`, `svelte`, `swiftui`, `react-native`, `flutter`, `shadcn`, `astro`, `nuxtjs`, `nuxt-ui`, `jetpack-compose`

## Домены поиска

| Домен | Для чего |
|-------|----------|
| `product` | Рекомендации по типу продукта |
| `style` | UI стили, эффекты |
| `typography` | Font pairings, Google Fonts |
| `color` | Цветовые палитры по индустриям |
| `landing` | Структура страниц, CTA |
| `chart` | Типы графиков |
| `ux` | Best practices, anti-patterns |

## Pre-Delivery Checklist

Перед сдачей UI проверь:

- [ ] Никаких эмодзи как иконок (используй SVG: Heroicons/Lucide)
- [ ] Все иконки из одного набора
- [ ] cursor-pointer на всех кликабельных элементах
- [ ] Hover states без layout shift
- [ ] Контраст текста минимум 4.5:1
- [ ] Glass элементы видны в light mode
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] Нет горизонтального скролла на мобильных
- [ ] Alt text на всех изображениях
- [ ] Labels на form inputs
- [ ] prefers-reduced-motion respected

## Файлы

- `search.py` — CLI интерфейс поиска
- `core.py` — BM25 поисковый движок
- `design_system.py` — генератор дизайн-систем
- `data/*.csv` — базы данных (стили, цвета, шрифты, стеки и т.д.)
