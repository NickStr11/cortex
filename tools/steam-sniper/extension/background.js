// Steam Sniper -- Background service worker
// Handles API calls to dashboard (content scripts can't fetch HTTP from HTTPS pages)

const API_BASE = "http://72.56.37.150";
const DEFAULT_USER = "lesha";

async function addToList(itemName, listType) {
  try {
    const res = await fetch(`${API_BASE}/api/lists`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user: DEFAULT_USER,
        item_name: itemName,
        list_type: listType,
      }),
    });
    const data = await res.json().catch(() => ({}));
    // /api/lists returns 201 on new, 200 if already exists — both are fine
    if ((res.status === 200 || res.status === 201) && data.ok !== false) {
      return { ok: true };
    }
    return { ok: false, error: data.error || `HTTP ${res.status}` };
  } catch (err) {
    return { ok: false, error: err.message || "Network error" };
  }
}

async function setTargets(itemName, listType, targetBelow, targetAbove) {
  try {
    const res = await fetch(`${API_BASE}/api/lists/target`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user: DEFAULT_USER,
        item_name: itemName,
        list_type: listType,
        target_below_rub: targetBelow,
        target_above_rub: targetAbove,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.ok !== false) {
      return { ok: true };
    }
    return { ok: false, error: data.error || `HTTP ${res.status}` };
  } catch (err) {
    return { ok: false, error: err.message || "Network error" };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === "addToList") {
    addToList(msg.item_name, msg.list_type).then(sendResponse);
    return true; // keep channel open for async response
  }
  if (msg.action === "setTargets") {
    setTargets(
      msg.item_name,
      msg.list_type,
      msg.target_below_rub,
      msg.target_above_rub
    ).then(sendResponse);
    return true;
  }
  return false;
});
