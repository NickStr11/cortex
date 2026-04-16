import { state } from './state.js';
import { events } from './events.js';

export function initChart() {
  // Chart: card click (event delegation)
  document.getElementById('watchlistArea').addEventListener('click', (e) => {
    const card = e.target.closest('.wl-card[data-item-name]');
    if (card && !e.target.closest('.wl-remove') && !e.target.closest('.wl-link')) {
      showChart(card.dataset.itemName);
    }
  });

  // Chart: timeframe buttons
  document.getElementById('chartTimeframes').addEventListener('click', async (e) => {
    const btn = e.target.closest('.tf-btn');
    if (!btn || !state.currentChartItem) return;
    state.currentTf = btn.dataset.tf;
    document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    await loadChart(state.currentChartItem, state.currentTf);
  });

  // Chart: close button
  document.getElementById('chartClose').addEventListener('click', hideChart);

  // Chart: resize handler
  window.addEventListener('resize', () => {
    if (state.chart) {
      const container = document.getElementById('chartContainer');
      state.chart.resize(container.clientWidth, 300);
    }
  });

  // Listen for chart:hide events (from modal Escape key)
  events.on('chart:hide', hideChart);
}

async function showChart(itemName) {
  state.currentChartItem = itemName;

  document.getElementById('chartPanel').style.display = '';
  document.getElementById('chartItemName').textContent = itemName;

  document.querySelectorAll('.wl-card[data-item-name]').forEach(c => c.classList.remove('selected'));
  const target = document.querySelector('.wl-card[data-item-name="' + CSS.escape(itemName) + '"]');
  if (target) target.classList.add('selected');

  if (!state.chart) {
    state.chart = LightweightCharts.createChart(document.getElementById('chartContainer'), {
      layout: {
        background: { type: 'solid', color: '#111b2e' },
        textColor: '#94a3b8',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(26, 39, 68, 0.5)' },
        horzLines: { color: 'rgba(26, 39, 68, 0.5)' },
      },
      rightPriceScale: { borderColor: '#1a2744' },
      timeScale: { borderColor: '#1a2744', timeVisible: true },
      crosshair: {
        vertLine: { color: 'rgba(255, 144, 106, 0.3)' },
        horzLine: { color: 'rgba(255, 144, 106, 0.3)' },
      },
    });
    state.lineSeries = state.chart.addSeries(LightweightCharts.LineSeries, {
      color: '#ff906a',
      lineWidth: 2,
      crosshairMarkerBackgroundColor: '#ff906a',
      priceFormat: { type: 'custom', formatter: (p) => Math.round(p).toLocaleString('ru-RU') + ' \u20BD' },
    });
  }

  await loadChart(itemName, state.currentTf);
}

async function loadChart(name, tf) {
  try {
    const r = await fetch('/api/history/' + encodeURIComponent(name) + '?tf=' + tf);
    const d = await r.json();
    const points = d.points || [];

    if (points.length === 0) {
      state.lineSeries.setData([]);
      document.getElementById('csMin').textContent = '\u2014';
      document.getElementById('csMax').textContent = '\u2014';
      document.getElementById('csAvg').textContent = '\u2014';
      document.getElementById('csCount').textContent = '\u2014';
      return;
    }

    const tvData = points.map(p => ({
      time: Math.floor(new Date(p.ts + 'Z').getTime() / 1000),
      value: p.price_usd * state.usdRub,
    })).sort((a, b) => a.time - b.time);

    state.lineSeries.setData(tvData);
    state.chart.timeScale().fitContent();

    const values = tvData.map(d => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((s, v) => s + v, 0) / values.length;

    document.getElementById('csMin').textContent = Math.round(min).toLocaleString('ru-RU') + ' \u20BD';
    document.getElementById('csMax').textContent = Math.round(max).toLocaleString('ru-RU') + ' \u20BD';
    document.getElementById('csAvg').textContent = Math.round(avg).toLocaleString('ru-RU') + ' \u20BD';
    document.getElementById('csCount').textContent = points.length;
  } catch (e) {
    console.error('loadChart:', e);
  }
}

function hideChart() {
  document.getElementById('chartPanel').style.display = 'none';
  document.querySelectorAll('.wl-card[data-item-name]').forEach(c => c.classList.remove('selected'));
  state.currentChartItem = null;
}
