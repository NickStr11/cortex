import { state } from './state.js';
import { fmtRub, fmtUsd } from './utils.js';
import { events } from './events.js';

export function openModal(item) {
  state.pendingItem = item;
  document.getElementById('searchResults').classList.remove('active');

  document.getElementById('modalName').textContent = item.name;
  document.getElementById('modalAvail').textContent = '\u0412 \u043D\u0430\u043B\u0438\u0447\u0438\u0438: ' + (item.count || '?') + ' \u0448\u0442';
  document.getElementById('modalPriceRub').textContent = fmtRub(item.price_rub);
  document.getElementById('modalPriceUsd').textContent = fmtUsd(item.price);
  document.getElementById('modalTarget').value = Math.round(item.price_rub || 0);
  document.getElementById('modalQty').value = 1;
  document.getElementById('modalType').value = 'buy';
  document.getElementById('modalDisplayName').value = item.name_ru || '';
  document.getElementById('modalCategory').value = item.type_ru || '';

  document.getElementById('modalOverlay').classList.add('active');
  document.getElementById('modalTarget').focus();
}

export function closeModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  state.pendingItem = null;
}

export async function addToWatchlist() {
  if (!state.pendingItem) return;

  const type = document.getElementById('modalType').value;
  const target_rub = parseFloat(document.getElementById('modalTarget').value);
  const qty = parseInt(document.getElementById('modalQty').value) || 1;

  if (!target_rub || target_rub <= 0) {
    document.getElementById('modalTarget').style.borderColor = 'var(--red)';
    return;
  }

  try {
    const r = await fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: state.pendingItem.name, type, target_rub, qty,
        display_name: document.getElementById('modalDisplayName').value || null,
        category: document.getElementById('modalCategory').value || null,
        image_url: state.pendingItem.image || null
      })
    });
    if (r.status === 201) {
      closeModal();
      document.getElementById('searchInput').value = '';
      document.getElementById('searchResults').classList.remove('active');
      events.emit('watchlist:changed');
    }
  } catch (e) { console.error('addToWatchlist:', e); }
}

export function initModal() {
  // Close modal on Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal();
      events.emit('chart:hide');
    }
  });

  // Wire modal buttons
  document.querySelector('.modal .btn-cancel').addEventListener('click', closeModal);
  document.querySelector('.modal .btn-primary').addEventListener('click', addToWatchlist);
}
