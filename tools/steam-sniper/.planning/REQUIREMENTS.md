# Requirements: Steam Sniper v2.0 -- Зеркало lis-skins

**Defined:** 2026-04-13
**Core Value:** Lesha opens dashboard and sees full lis-skins catalog as his own -- with categories, personal lists, prices, and alerts

## v2.0 Requirements

### Refactoring

- [x] **REF-01**: Dashboard split на ES модули (router, catalog, lists, charts, watchlist) -- без изменения функциональности
- [x] **REF-02**: Общий UI-фреймворк: tab router (hash-based), shared state, event bus

### Catalog

- [x] **CAT-01**: Category parser определяет категорию предмета из CS2 имени (ножи, винтовки, пистолеты, перчатки, стикеры, кейсы, агенты, граффити, музыка, патчи, ключи)
- [x] **CAT-02**: GET /api/catalog с серверной пагинацией (limit/offset), фильтром по категории, поиском по имени
- [x] **CAT-03**: Каталог-view в дашборде: карточки предметов с ценой, картинкой, категорией, наличием
- [x] **CAT-04**: Sidebar навигация по категориям с количеством предметов в каждой
- [x] **CAT-05**: Сортировка каталога: по цене (up/down), по имени, по наличию

### Personal Lists

- [x] **LIST-01**: Таблица user_lists в SQLite (отдельно от watchlist) -- user_id, item_name, list_type (favorite/wishlist), added_at
- [x] **LIST-02**: POST/DELETE /api/lists -- добавление/удаление из списка
- [x] **LIST-03**: GET /api/lists?user=&type= -- получение списка пользователя
- [x] **LIST-04**: Кнопки heart (избранное) и star (хотелки) на каждой карточке каталога -- toggle одним кликом
- [x] **LIST-05**: Отдельные табы "Избранное" и "Хотелки" с отображением только своих предметов
- [x] **LIST-06**: Индикатор на карточке каталога показывает в каком списке предмет уже есть

### Cases

- [x] **CASE-01**: Отдельный таб "Кейсы" -- фильтрованный каталог (category=case)
- [x] **CASE-02**: Карточки кейсов с ценой, наличием, трендом цены

### PWA

- [x] **PWA-01**: manifest.json с иконками (192x192, 512x512), standalone display mode, темная тема
- [x] **PWA-02**: Service worker (network-first для HTML/API, cache-first для статики)
- [x] **PWA-03**: HTTPS на VPS (nginx reverse proxy + Let's Encrypt) -- необходим для service worker на iOS

### Chrome Extension

- [x] **EXT-01**: Manifest V3 extension с content script для lis-skins.com
- [x] **EXT-02**: Кнопка "Add to Sniper" инжектится на страницах предметов lis-skins.com
- [x] **EXT-03**: Background service worker отправляет POST на dashboard API при клике
- [x] **EXT-04**: Visual feedback после добавления (success/error notification)

## v3 Requirements (deferred)

- **STEAM-01**: Steam Market цены + сравнение с lis-skins (blocked: нужен Steam-аккаунт)
- **STEAM-02**: Кросс-площадочный арбитраж (Steam vs lis-skins дельта)
- **CASECONT-01**: Содержимое кейсов и drop rates (нужен внешний API)
- **PROFIT-01**: Калькулятор прибыли с учетом комиссии lis-skins
- **NOTE-01**: Заметки к предметам (стратегия, почему добавил)
- **MULTI-01**: Разделение watchlist по пользователям (?user=lesha)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Steam Market интеграция | Blocked: нужен отдельный Steam-аккаунт от Лёши |
| Авторизация/логин | 2 пользователя, приватный URL |
| Мобильное приложение | PWA достаточно |
| ML-сигналы | Может в будущем |
| Публикация extension в Chrome Web Store | 2 пользователя, unpacked loading |
| Offline mode | Цены бессмысленны без интернета |
| Drop rates кейсов | Внешний API, defer to v3 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REF-01 | Phase 5 | Complete |
| REF-02 | Phase 5 | Complete |
| CAT-01 | Phase 6 | Complete |
| CAT-02 | Phase 6 | Complete |
| CAT-03 | Phase 8 | Complete |
| CAT-04 | Phase 8 | Complete |
| CAT-05 | Phase 6 | Complete |
| LIST-01 | Phase 7 | Complete |
| LIST-02 | Phase 7 | Complete |
| LIST-03 | Phase 7 | Complete |
| LIST-04 | Phase 8 | Complete |
| LIST-05 | Phase 8 | Complete |
| LIST-06 | Phase 8 | Complete |
| CASE-01 | Phase 9 | Complete |
| CASE-02 | Phase 9 | Complete |
| PWA-01 | Phase 9 | Complete |
| PWA-02 | Phase 9 | Complete |
| PWA-03 | Phase 9 | Complete |
| EXT-01 | Phase 10 | Complete |
| EXT-02 | Phase 10 | Complete |
| EXT-03 | Phase 10 | Complete |
| EXT-04 | Phase 10 | Complete |

**Coverage:**
- v2.0 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation*
