// Steam Sniper -- Content script for lis-skins.com
// Injects "Add to Sniper" button on item pages

(function () {
  "use strict";

  let lastUrl = location.href;
  let checkCount = 0;
  const MAX_CHECKS = 5;
  const CHECK_INTERVAL = 2000;

  /** Extract item name from page DOM / title. Returns null if not found. */
  function getItemName() {
    // Try h1 first (most reliable on item pages)
    const h1 = document.querySelector("h1");
    if (h1 && h1.textContent.trim()) {
      return h1.textContent.trim();
    }

    // Try common class patterns
    const selectors = [
      ".market-item-name",
      ".item-name",
      "[class*='item-name']",
      "[class*='ItemName']",
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.textContent.trim()) {
        return el.textContent.trim();
      }
    }

    // Fallback: page title, strip site suffix
    const title = document.title;
    if (title) {
      return title
        .replace(/\s*[-|]\s*lis-skins\.com\s*/i, "")
        .replace(/\s*[-|]\s*Lis-Skins\s*/i, "")
        .trim();
    }

    return null;
  }

  /** Check if current page looks like an item page. */
  function isItemPage() {
    // URL must contain /market/ to be a catalog/item page
    return /\/market\//i.test(location.pathname);
  }

  /** Show toast notification. */
  function showToast(message, isError) {
    // Remove existing toast
    const existing = document.querySelector(".sniper-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className =
      "sniper-toast " + (isError ? "sniper-error" : "sniper-success");
    toast.textContent = message;
    document.body.appendChild(toast);

    // Auto-hide after 3 seconds
    setTimeout(() => {
      toast.classList.add("sniper-fade-out");
      setTimeout(() => toast.remove(), 400);
    }, 3000);
  }

  /** Send item to dashboard API via background worker. */
  function addToList(itemName, listType) {
    chrome.runtime.sendMessage(
      { action: "addToList", item_name: itemName, list_type: listType },
      (response) => {
        if (chrome.runtime.lastError) {
          showToast("Extension error: " + chrome.runtime.lastError.message, true);
          return;
        }
        if (response && response.ok) {
          const label = listType === "favorite" ? "favorites" : "wishlist";
          showToast("Added to " + label, false);
        } else {
          showToast(
            "Error: " + (response ? response.error : "No response"),
            true
          );
        }
      }
    );
  }

  /** Inject the "Add to Sniper" button into the page. */
  function injectButton() {
    // Duplicate prevention
    if (document.querySelector(".sniper-btn-container")) {
      return;
    }

    if (!isItemPage()) {
      return;
    }

    const itemName = getItemName();
    if (!itemName) {
      return;
    }

    // Container
    const container = document.createElement("div");
    container.className = "sniper-btn-container";

    // Main button
    const btn = document.createElement("button");
    btn.className = "sniper-btn";
    btn.textContent = "Add to Sniper";

    // Dropdown
    const dropdown = document.createElement("div");
    dropdown.className = "sniper-dropdown";

    const favItem = document.createElement("div");
    favItem.className = "sniper-dropdown-item";
    favItem.textContent = "Favorite";
    favItem.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.remove("sniper-show");
      addToList(itemName, "favorite");
    });

    const wishItem = document.createElement("div");
    wishItem.className = "sniper-dropdown-item";
    wishItem.textContent = "Wishlist";
    wishItem.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.remove("sniper-show");
      addToList(itemName, "wishlist");
    });

    dropdown.appendChild(favItem);
    dropdown.appendChild(wishItem);

    // Toggle dropdown on button click
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("sniper-show");
    });

    // Close dropdown on outside click
    document.addEventListener("click", () => {
      dropdown.classList.remove("sniper-show");
    });

    container.appendChild(dropdown);
    container.appendChild(btn);
    document.body.appendChild(container);
  }

  /** Handle SPA navigation: re-inject if URL changed. */
  function checkForNavigation() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      // Remove old button (new page)
      const old = document.querySelector(".sniper-btn-container");
      if (old) old.remove();
      // Re-inject
      injectButton();
    }
  }

  // Initial injection
  injectButton();

  // SPA handling: poll for URL changes (lis-skins may use client-side routing)
  const interval = setInterval(() => {
    checkCount++;
    checkForNavigation();
    if (checkCount >= MAX_CHECKS) {
      clearInterval(interval);
    }
  }, CHECK_INTERVAL);

  // Also observe DOM mutations for SPA navigation (more reliable than polling)
  const observer = new MutationObserver(() => {
    checkForNavigation();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
