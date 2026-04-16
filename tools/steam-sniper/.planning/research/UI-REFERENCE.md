# UI Reference

## Source
Google Stitch design: https://stitch.withgoogle.com/projects/17808703029072340772
HTML reference saved: `.planning/research/kinetic-armory.html`

## Design Decisions
- **Base theme**: Dark (#0e0e0e bg, #131313 sidebar, #1a1919 cards)
- **Primary accent**: Orange #ff906a (matches current Steam Sniper)
- **Fonts**: Rajdhani (display) + JetBrains Mono (data) — NOT Plus Jakarta Sans
- **Layout**: Sidebar nav + top header + main content
- **Pages**: Dashboard (overview), Watchlist (main), Item detail (chart)

## Components to implement
1. Top header: logo, search, stats (USD/RUB, items count, last update)
2. Sidebar: Dashboard, Watchlist, навигация
3. Hero section: total portfolio value + delta %
4. Item cards: name, wear, price in RUB, delta, category color
5. Chart: TradingView Lightweight Charts (item detail page)
6. Activity feed: recent alerts from bot
7. Watchlist table: full list with current prices, targets, deltas

## Not implementing
- Trade Items button (no auto-trade)
- Login/Logout (no auth)
- User avatar/profile
- Collection breakdown pie chart (v2 maybe)
