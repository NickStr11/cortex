const USER = 'lesha';

function alertCounts(watchlist) {
  let buyReady = 0;
  let sellReady = 0;
  for (const it of watchlist.buy || []) {
    if (it.current_price_rub != null && it.target_rub != null && it.current_price_rub <= it.target_rub) buyReady++;
  }
  for (const it of watchlist.sell || []) {
    if (it.current_price_rub != null && it.target_rub != null && it.current_price_rub >= it.target_rub) sellReady++;
  }
  return { buyReady, sellReady };
}

function listAlertCounts(items) {
  let buyReady = 0;
  let sellReady = 0;
  for (const item of items || []) {
    if (item.alert_below_triggered) buyReady++;
    if (item.alert_above_triggered) sellReady++;
  }
  return { buyReady, sellReady };
}

export async function loadStats() {
  try {
    const [wl, fav, wish] = await Promise.all([
      fetch('/api/watchlist').then(r => r.json()),
      fetch(`/api/lists?user=${USER}&type=favorite`).then(r => r.json()),
      fetch(`/api/lists?user=${USER}&type=wishlist`).then(r => r.json()),
    ]);

    const favCount = (fav.items || []).length;
    const wishCount = (wish.items || []).length;
    const watchlistCounts = alertCounts(wl);
    const favoriteCounts = listAlertCounts(fav.items || []);
    const wishlistCounts = listAlertCounts(wish.items || []);
    const buyReady = watchlistCounts.buyReady + favoriteCounts.buyReady + wishlistCounts.buyReady;
    const sellReady = watchlistCounts.sellReady + favoriteCounts.sellReady + wishlistCounts.sellReady;

    document.getElementById('heroValue').textContent = favCount;
    document.getElementById('heroDelta').textContent = wishCount;

    const card = document.getElementById('heroAlertsCard');
    const value = document.getElementById('heroCount');
    card.classList.remove('alert-buy', 'alert-sell', 'alert-both');

    if (buyReady > 0 && sellReady > 0) {
      value.innerHTML = `<span class="alert-dot alert-dot-buy"></span>${buyReady}&nbsp;&nbsp;<span class="alert-dot alert-dot-sell"></span>${sellReady}`;
      card.classList.add('alert-both');
    } else if (buyReady > 0) {
      value.innerHTML = `<span class="alert-dot alert-dot-buy"></span>${buyReady}`;
      card.classList.add('alert-buy');
    } else if (sellReady > 0) {
      value.innerHTML = `<span class="alert-dot alert-dot-sell"></span>${sellReady}`;
      card.classList.add('alert-sell');
    } else {
      value.textContent = '—';
    }
  } catch (e) {
    console.error('loadStats:', e);
  }
}
