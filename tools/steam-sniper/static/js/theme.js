const KEY = 'ss:theme';

function applyTheme(theme) {
  const t = theme === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', t === 'light' ? '#eef2f8' : '#060a12');
}

export function initTheme() {
  const saved = localStorage.getItem(KEY) || 'dark';
  applyTheme(saved);

  const btn = document.getElementById('themeToggle');
  if (!btn) return;

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const next = current === 'light' ? 'dark' : 'light';
    localStorage.setItem(KEY, next);
    applyTheme(next);
  });
}
