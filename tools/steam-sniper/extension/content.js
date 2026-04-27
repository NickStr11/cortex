// Steam Sniper -- Content script for lis-skins.com
// Injects "Add to Sniper" button with inline target-price form on item pages

(function () {
  "use strict";

  let lastUrl = location.href;
  let checkCount = 0;
  const MAX_CHECKS = 5;
  const CHECK_INTERVAL = 2000;

  function hasWearMarker(text) {
    return /\((factory new|minimal wear|field-tested|well-worn|battle-scarred|прямо с завода|немного поношенн(?:ое|ый)|после полевых(?: испытаний)?|послеполевые|поношенн(?:ое|ый)|закал[её]нн(?:ое|ый) в боях)\)/i.test(text || "");
  }

  function cleanTitle(text) {
    return (text || "")
      .replace(/\s*[-|]\s*lis-skins\.com\s*/i, "")
      .replace(/\s*[-|]\s*Lis-Skins\s*/i, "")
      .trim();
  }

  /** Extract item name from page DOM / title. Returns null if not found. */
  function getItemName() {
    const candidates = [];
    document.querySelectorAll("h1").forEach((el) => {
      const text = el.textContent.trim();
      if (text) candidates.push(text);
    });
    const selectors = [
      ".market-item-name",
      ".item-name",
      "[class*='item-name']",
      "[class*='ItemName']",
    ];
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        const text = el.textContent.trim();
        if (text) candidates.push(text);
      });
    }
    const title = cleanTitle(document.title);
    if (title) {
      candidates.push(title);
    }

    return candidates.find(hasWearMarker) || candidates[0] || null;
  }

  function isItemPage() {
    return /\/market\//i.test(location.pathname);
  }

  function showToast(message, isError) {
    const existing = document.querySelector(".sniper-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.className =
      "sniper-toast " + (isError ? "sniper-error" : "sniper-success");
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("sniper-fade-out");
      setTimeout(() => toast.remove(), 400);
    }, 3000);
  }

  /** Parse price input: accept "1234", "1 234", "1 234,50", "1234.5". */
  function parsePrice(raw) {
    if (!raw) return null;
    const cleaned = String(raw).replace(/\s/g, "").replace(",", ".");
    if (cleaned === "") return null;
    const num = parseFloat(cleaned);
    if (isNaN(num) || num <= 0) return NaN; // invalid
    return num;
  }

  /** Send POST /api/lists via background worker. */
  function addToListRequest(itemName, listType) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: "addToList", item_name: itemName, list_type: listType },
        (response) => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false, error: "No response" });
        }
      );
    });
  }

  /** Send PATCH /api/lists/target via background worker. */
  function setTargetsRequest(itemName, listType, targetBelow, targetAbove) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        {
          action: "setTargets",
          item_name: itemName,
          list_type: listType,
          target_below_rub: targetBelow,
          target_above_rub: targetAbove,
        },
        (response) => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false, error: "No response" });
        }
      );
    });
  }

  /** Close the inline target-price form if open. */
  function closeTargetForm() {
    const form = document.querySelector(".sniper-target-form");
    if (form) form.remove();
  }

  /**
   * Render inline target-price form under the main button.
   * User can type target_below / target_above and press Add, or Skip to add without targets.
   */
  function showTargetForm(container, itemName, listType) {
    closeTargetForm();

    const form = document.createElement("div");
    form.className = "sniper-target-form";

    const title = document.createElement("div");
    title.className = "sniper-target-title";
    const listLabel = listType === "favorite" ? "Избранное" : "Хотелки";
    title.textContent = `${listLabel} — цели (₽, необязательно)`;
    form.appendChild(title);

    const belowRow = document.createElement("div");
    belowRow.className = "sniper-target-row";
    const belowLabel = document.createElement("span");
    belowLabel.className = "sniper-target-label sniper-target-below";
    belowLabel.textContent = "🔴 Ниже";
    const belowInput = document.createElement("input");
    belowInput.type = "text";
    belowInput.inputMode = "decimal";
    belowInput.placeholder = "напр. 2100";
    belowInput.className = "sniper-target-input";
    belowRow.appendChild(belowLabel);
    belowRow.appendChild(belowInput);
    form.appendChild(belowRow);

    const aboveRow = document.createElement("div");
    aboveRow.className = "sniper-target-row";
    const aboveLabel = document.createElement("span");
    aboveLabel.className = "sniper-target-label sniper-target-above";
    aboveLabel.textContent = "🟢 Выше";
    const aboveInput = document.createElement("input");
    aboveInput.type = "text";
    aboveInput.inputMode = "decimal";
    aboveInput.placeholder = "напр. 3400";
    aboveInput.className = "sniper-target-input";
    aboveRow.appendChild(aboveLabel);
    aboveRow.appendChild(aboveInput);
    form.appendChild(aboveRow);

    const btnRow = document.createElement("div");
    btnRow.className = "sniper-target-buttons";
    const addBtn = document.createElement("button");
    addBtn.className = "sniper-mini-btn sniper-mini-add";
    addBtn.textContent = "Добавить";
    const skipBtn = document.createElement("button");
    skipBtn.className = "sniper-mini-btn sniper-mini-skip";
    skipBtn.textContent = "Без целей";
    btnRow.appendChild(addBtn);
    btnRow.appendChild(skipBtn);
    form.appendChild(btnRow);

    async function submit(withTargets) {
      let below = null;
      let above = null;
      if (withTargets) {
        below = parsePrice(belowInput.value);
        above = parsePrice(aboveInput.value);
        if (Number.isNaN(below) || Number.isNaN(above)) {
          showToast("Цена должна быть числом > 0", true);
          return;
        }
        if (below !== null && above !== null && below >= above) {
          showToast("🔴 должна быть меньше 🟢", true);
          return;
        }
      }

      addBtn.disabled = true;
      skipBtn.disabled = true;
      addBtn.textContent = "Отправка...";

      const addResp = await addToListRequest(itemName, listType);
      if (!addResp.ok) {
        showToast("Ошибка: " + (addResp.error || "не добавлено"), true);
        addBtn.disabled = false;
        skipBtn.disabled = false;
        addBtn.textContent = "Добавить";
        return;
      }

      if (withTargets && (below !== null || above !== null)) {
        const targetResp = await setTargetsRequest(
          itemName,
          listType,
          below,
          above
        );
        if (!targetResp.ok) {
          // Item added but targets failed — partial success
          showToast(
            "Добавлено, но цели не сохранились: " +
              (targetResp.error || "ошибка"),
            true
          );
          closeTargetForm();
          return;
        }
        const parts = [];
        if (below !== null) parts.push(`🔴 ${below} ₽`);
        if (above !== null) parts.push(`🟢 ${above} ₽`);
        showToast(
          `Добавлено в ${listLabel.toLowerCase()} (${parts.join(", ")})`,
          false
        );
      } else {
        showToast(`Добавлено в ${listLabel.toLowerCase()}`, false);
      }
      closeTargetForm();
    }

    addBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      submit(true);
    });
    skipBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      submit(false);
    });

    // Enter in any input = Add with targets
    [belowInput, aboveInput].forEach((inp) => {
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          submit(true);
        }
        if (e.key === "Escape") {
          e.preventDefault();
          closeTargetForm();
        }
      });
      inp.addEventListener("click", (e) => e.stopPropagation());
    });

    container.appendChild(form);
    belowInput.focus();
  }

  /** Inject the main "Add to Sniper" button with dropdown. */
  function injectButton() {
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

    const container = document.createElement("div");
    container.className = "sniper-btn-container";

    const btn = document.createElement("button");
    btn.className = "sniper-btn";
    btn.textContent = "Add to Sniper";

    const dropdown = document.createElement("div");
    dropdown.className = "sniper-dropdown";

    const favItem = document.createElement("div");
    favItem.className = "sniper-dropdown-item";
    favItem.textContent = "Favorite";
    favItem.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.remove("sniper-show");
      showTargetForm(container, itemName, "favorite");
    });

    const wishItem = document.createElement("div");
    wishItem.className = "sniper-dropdown-item";
    wishItem.textContent = "Wishlist";
    wishItem.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.remove("sniper-show");
      showTargetForm(container, itemName, "wishlist");
    });

    dropdown.appendChild(favItem);
    dropdown.appendChild(wishItem);

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("sniper-show");
    });

    document.addEventListener("click", () => {
      dropdown.classList.remove("sniper-show");
    });

    container.appendChild(dropdown);
    container.appendChild(btn);
    document.body.appendChild(container);
  }

  function checkForNavigation() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      const old = document.querySelector(".sniper-btn-container");
      if (old) old.remove();
      closeTargetForm();
      injectButton();
    }
  }

  injectButton();

  const interval = setInterval(() => {
    checkCount++;
    checkForNavigation();
    if (checkCount >= MAX_CHECKS) {
      clearInterval(interval);
    }
  }, CHECK_INTERVAL);

  const observer = new MutationObserver(() => {
    checkForNavigation();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
