(function () {
  "use strict";

  const config = window.APP_CONFIG || {};
  const messages = config.messages || {};
  const accountsBody = document.querySelector("#accounts-body");
  const emptyState = document.querySelector("#empty-state");
  const flashMessage = document.querySelector("#flash-message");
  const registerForm = document.querySelector("#register-form");
  const accountDetailsDialog = document.querySelector("#account-details");
  const manualCopyDialog = document.querySelector("#manual-copy");
  const manualCopyText = document.querySelector("#manual-copy-text");
  const accountStore = new Map();
  const pollQueue = [];
  const activePolls = new Map();
  const maxPolls = 20;
  const pollIntervalMs = 2500;
  const dbName = "matuya-register";
  const dbVersion = 1;

  document.querySelector('form[action$="/logout"]')?.addEventListener("submit", function () {
    if ("indexedDB" in window) {
      indexedDB.deleteDatabase(dbName);
    }
    if ("caches" in window) {
      caches.keys().then(function (keys) {
        keys.forEach(function (key) {
          caches.delete(key);
        });
      });
    }
  });

  if (!accountsBody) {
    registerServiceWorker();
    return;
  }

  function msg(key, fallback, args) {
    let value = messages[key] || fallback || key;
    Object.keys(args || {}).forEach(function (name) {
      value = value.replace("{" + name + "}", args[name]);
    });
    return value;
  }

  function showMessage(text, isError) {
    if (!flashMessage) {
      return;
    }
    flashMessage.textContent = text || "";
    flashMessage.style.color = isError ? "#b42318" : "#176b5b";
  }

  function headers() {
    return {
      "Content-Type": "application/json",
      "X-CSRF-Token": config.csrfToken || "",
      Accept: "application/json",
    };
  }

  async function requestJson(url, options) {
    const response = await fetch(url, Object.assign({ credentials: "same-origin" }, options));
    const payload = await response.json().catch(function () {
      return {};
    });
    if (!response.ok) {
      throw new Error(payload.message || msg("error.api.generic", "Request failed."));
    }
    return payload;
  }

  function currentBucket() {
    return new URLSearchParams(window.location.search).get("bucket") || "unused";
  }

  function accountId(account) {
    return account && account.id !== undefined && account.id !== null ? String(account.id) : "";
  }

  function shouldShow(account) {
    return (account.bucket || "unused") === currentBucket();
  }

  function shouldPoll(account) {
    const status = account.raw_status || account.status;
    return status === "pending" || status === "running";
  }

  function rememberAccount(account) {
    const id = accountId(account);
    if (!id) {
      return;
    }
    const merged = Object.assign({}, accountStore.get(id) || {}, account);
    accountStore.set(id, merged);
    cacheAccount(merged);
  }

  function updateEmptyState() {
    if (emptyState) {
      emptyState.hidden = accountsBody.querySelectorAll("[data-account-id]").length > 0;
    }
  }

  function statusText(status) {
    return msg("status." + status, status);
  }

  function renderRow(account) {
    const row = document.createElement("button");
    const email = document.createElement("span");
    const status = document.createElement("span");
    row.type = "button";
    row.className = "account-row";
    row.dataset.accountId = account.id;
    row.dataset.details = "";
    email.className = "account-row-email";
    status.className = "status-pill";
    status.dataset.field = "status";
    row.appendChild(email);
    row.appendChild(status);
    updateRow(row, account);
    return row;
  }

  function updateRow(row, account) {
    rememberAccount(account);
    row.dataset.status = account.status;
    row.querySelector(".account-row-email").textContent = account.email || "";
    row.querySelector('[data-field="status"]').textContent = statusText(account.status);
    if (detailsAreOpen() && accountDetailsDialog.dataset.accountId === accountId(account)) {
      renderDetails(account);
    }
  }

  function upsertAccount(account, prepend) {
    rememberAccount(account);
    let row = accountsBody.querySelector('[data-account-id="' + account.id + '"]');
    if (row) {
      updateRow(row, account);
    } else if (shouldShow(account)) {
      row = renderRow(account);
      if (prepend && accountsBody.firstChild) {
        accountsBody.insertBefore(row, accountsBody.firstChild);
      } else {
        accountsBody.appendChild(row);
      }
    }
    updateEmptyState();
    if (shouldPoll(account)) {
      enqueuePoll(account.id);
    } else {
      stopPoll(account.id);
    }
  }

  function detailsAreOpen() {
    return accountDetailsDialog && !accountDetailsDialog.hidden;
  }

  function manualCopyIsOpen() {
    return manualCopyDialog && !manualCopyDialog.hidden;
  }

  function detailValue(account, field) {
    if (field === "status") {
      return statusText(account.status);
    }
    if (field === "email_copy_count" || field === "password_copy_count") {
      return String(account[field] || 0);
    }
    return account[field] || "-";
  }

  function renderDetails(account) {
    if (!accountDetailsDialog) {
      return;
    }
    accountDetailsDialog.dataset.accountId = accountId(account);
    accountDetailsDialog.querySelectorAll("[data-detail-field]").forEach(function (field) {
      field.textContent = detailValue(account, field.dataset.detailField);
    });
  }

  function openDetails(row) {
    if (!accountDetailsDialog || !row) {
      return;
    }
    const account = accountStore.get(row.dataset.accountId);
    if (!account) {
      return;
    }
    renderDetails(account);
    accountDetailsDialog.hidden = false;
    document.body.classList.add("details-open");
    accountDetailsDialog.querySelector("[data-detail-copy]")?.focus();
  }

  function closeDetails() {
    if (!accountDetailsDialog) {
      return;
    }
    accountDetailsDialog.hidden = true;
    document.body.classList.remove("details-open");
  }

  function openManualCopy(text) {
    if (!manualCopyDialog || !manualCopyText) {
      return;
    }
    manualCopyText.value = text || "";
    manualCopyDialog.hidden = false;
    document.body.classList.add("details-open");
    manualCopyText.focus();
    manualCopyText.select();
  }

  function closeManualCopy() {
    if (!manualCopyDialog) {
      return;
    }
    manualCopyDialog.hidden = true;
    if (!detailsAreOpen()) {
      document.body.classList.remove("details-open");
    }
  }

  async function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (error) {
        // Some mobile browsers expose the API while denying writes.
      }
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    const copied = document.execCommand("copy");
    document.body.removeChild(textarea);
    if (!copied) {
      openManualCopy(text);
      return false;
    }
    return true;
  }

  async function recordCopy(accountIdValue, kind) {
    const payload = await requestJson("/api/accounts/" + accountIdValue + "/copy-" + kind, {
      method: "POST",
      headers: headers(),
      body: "{}",
    });
    upsertAccount(payload.account, false);
  }

  function enqueuePoll(accountIdValue) {
    if (activePolls.has(accountIdValue) || pollQueue.includes(accountIdValue)) {
      return;
    }
    pollQueue.push(accountIdValue);
    drainPollQueue();
  }

  function drainPollQueue() {
    while (activePolls.size < maxPolls && pollQueue.length > 0) {
      const id = pollQueue.shift();
      pollAccount(id);
      activePolls.set(id, window.setInterval(function () {
        pollAccount(id);
      }, pollIntervalMs));
    }
  }

  function stopPoll(accountIdValue) {
    const timer = activePolls.get(accountIdValue);
    if (timer) {
      window.clearInterval(timer);
      activePolls.delete(accountIdValue);
      drainPollQueue();
    }
  }

  async function pollAccount(accountIdValue) {
    try {
      const payload = await requestJson("/api/accounts/" + accountIdValue, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      upsertAccount(payload.account, false);
      if (!shouldPoll(payload.account)) {
        stopPoll(accountIdValue);
      }
    } catch (error) {
      stopPoll(accountIdValue);
      showMessage(error.message, true);
    }
  }

  function setBusy(form, busy) {
    Array.from(form.elements).forEach(function (element) {
      element.disabled = busy;
    });
  }

  registerForm?.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (!navigator.onLine) {
      showMessage(msg("accounts.online_required", "Network is required to register."), true);
      return;
    }
    const form = event.currentTarget;
    const data = new FormData(form);
    const count = Number(data.get("count") || 1);
    setBusy(form, true);
    showMessage("", false);
    try {
      const payload = await requestJson("/api/register-batch", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ count: count }),
      });
      payload.accounts.forEach(function (account) {
        upsertAccount(account, true);
      });
      const failedCount = payload.accounts.filter(function (account) {
        return account.bucket === "failed" || account.status === "failed";
      }).length;
      const messageKey = failedCount > 0 ? "accounts.batch_created_with_failures" : "accounts.batch_started";
      const fallback =
        failedCount > 0
          ? "Created {count} account records. {failed} failed; check Failed."
          : "Started {count} registration tasks.";
      showMessage(
        msg(messageKey, fallback, {
          count: payload.accounts.length,
          failed: failedCount,
        }),
        failedCount > 0
      );
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      setBusy(form, false);
    }
  });

  accountsBody.addEventListener("click", function (event) {
    const row = event.target.closest("[data-details]");
    if (row) {
      openDetails(row);
    }
  });

  accountDetailsDialog?.addEventListener("click", async function (event) {
    const copyButton = event.target.closest("[data-detail-copy]");
    if (copyButton) {
      const kind = copyButton.dataset.detailCopy;
      const id = accountDetailsDialog.dataset.accountId;
      const account = accountStore.get(id) || {};
      const text = account[kind] || "";
      copyButton.disabled = true;
      try {
        const copied = await copyText(text);
        if (copied) {
          await recordCopy(id, kind);
        }
        showMessage(
          copied
            ? msg("accounts.copy_success", "Copied.")
            : msg("accounts.manual_copy_opened", "Copy permission was denied. Select and copy the text manually."),
          !copied
        );
      } catch (error) {
        showMessage(error.message || msg("accounts.copy_failed", "Copy failed."), true);
      } finally {
        copyButton.disabled = false;
      }
      return;
    }
    if (event.target.closest("[data-details-close]") || event.target === accountDetailsDialog) {
      closeDetails();
    }
  });

  manualCopyDialog?.addEventListener("click", function (event) {
    if (event.target.closest("[data-manual-copy-close]") || event.target === manualCopyDialog) {
      closeManualCopy();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && manualCopyIsOpen()) {
      closeManualCopy();
    } else if (event.key === "Escape" && detailsAreOpen()) {
      closeDetails();
    }
  });

  function openDb() {
    if (!("indexedDB" in window)) {
      return Promise.resolve(null);
    }
    return new Promise(function (resolve) {
      const request = indexedDB.open(dbName, dbVersion);
      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains("accounts")) {
          const store = db.createObjectStore("accounts", { keyPath: "id" });
          store.createIndex("bucket", "bucket", { unique: false });
        }
      };
      request.onsuccess = function () {
        resolve(request.result);
      };
      request.onerror = function () {
        resolve(null);
      };
    });
  }

  async function cacheAccount(account) {
    const db = await openDb();
    if (!db) {
      return;
    }
    const tx = db.transaction("accounts", "readwrite");
    tx.objectStore("accounts").put(Object.assign({ cached_at: Date.now() }, account));
  }

  async function loadCachedAccounts() {
    const db = await openDb();
    if (!db) {
      return [];
    }
    return new Promise(function (resolve) {
      const tx = db.transaction("accounts", "readonly");
      const request = tx.objectStore("accounts").getAll();
      request.onsuccess = function () {
        resolve((request.result || []).filter(shouldShow));
      };
      request.onerror = function () {
        resolve([]);
      };
    });
  }

  async function hydrateFromCacheIfUseful() {
    if (accountsBody.children.length > 0 && navigator.onLine) {
      return;
    }
    const cached = await loadCachedAccounts();
    cached
      .sort(function (a, b) {
        return String(b.created_at || "").localeCompare(String(a.created_at || ""));
      })
      .forEach(function (account) {
        upsertAccount(account, false);
      });
    if (cached.length > 0 && !navigator.onLine) {
      showMessage(msg("accounts.offline_cache", "Showing cached accounts."), false);
    }
  }

  function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/service-worker.js").catch(function () {});
    }
  }

  (config.accounts || []).forEach(function (account) {
    upsertAccount(account, false);
  });
  hydrateFromCacheIfUseful();
  registerServiceWorker();
  updateEmptyState();
})();
