// Steam Sniper -- Background service worker
// Handles API calls to dashboard (content scripts can't fetch HTTP from HTTPS pages)

const API_BASE = "http://72.56.37.150";
const DEFAULT_USER = "lesha";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action !== "addToList") {
    return false;
  }

  const body = JSON.stringify({
    user: DEFAULT_USER,
    item_name: msg.item_name,
    list_type: msg.list_type,
  });

  fetch(`${API_BASE}/api/lists`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  })
    .then((res) => res.json().then((data) => ({ status: res.status, data })))
    .then(({ status, data }) => {
      if (status === 201 && data.ok) {
        sendResponse({ ok: true });
      } else {
        sendResponse({ ok: false, error: data.error || `HTTP ${status}` });
      }
    })
    .catch((err) => {
      sendResponse({ ok: false, error: err.message || "Network error" });
    });

  // CRITICAL: return true to keep message channel open for async sendResponse
  return true;
});
