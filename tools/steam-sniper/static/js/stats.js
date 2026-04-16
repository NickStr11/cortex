import { fmtRub, fmtDelta } from './utils.js';

export async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('heroValue').textContent = fmtRub(d.total_value_rub);
    const delta = fmtDelta(d.delta_pct);
    const heroEl = document.getElementById('heroDelta');
    heroEl.textContent = delta.text;
    heroEl.className = 'hc-value' + (delta.cls === 'up' ? ' positive' : delta.cls === 'down' ? ' negative' : '');
    document.getElementById('heroCount').textContent = d.total_items || 0;
  } catch (e) { console.error('loadStats:', e); }
}
