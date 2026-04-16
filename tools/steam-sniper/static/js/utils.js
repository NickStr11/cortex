export function fmtRub(val) {
  if (val == null) return '-- \u20BD';
  return Math.round(val).toLocaleString('ru-RU') + ' \u20BD';
}

export function fmtUsd(val) {
  if (val == null) return '--';
  return '$' + val.toFixed(2);
}

export function fmtDelta(val) {
  if (val == null) return { text: '--', cls: '' };
  const text = (val > 0 ? '+' : '') + val.toFixed(1) + '%';
  const cls = val > 0.05 ? 'up' : val < -0.05 ? 'down' : '';
  return { text, cls };
}

export function timeAgo(ts) {
  if (!ts) return '';
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return mins + 'm ago';
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + 'h ago';
  return Math.floor(hrs / 24) + 'd ago';
}
