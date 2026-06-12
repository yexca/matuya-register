(function () {
  "use strict";

  const config = window.APP_CONFIG || {};
  const messages = config.messages || {};
  const accountsBody = document.querySelector("#accounts-body");
  const emptyState = document.querySelector("#empty-state");
  const flashMessage = document.querySelector("#flash-message");
  const accountDetailsDialog = document.querySelector("#account-details");
  const manualCopyDialog = document.querySelector("#manual-copy");
  const manualCopyText = document.querySelector("#manual-copy-text");
  const accountStore = new Map();
  const pollQueue = [];
  const activePolls = new Map();
  const maxPolls = 20;
  const pollIntervalMs = 2500;

  if (!accountsBody) {
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

  function setBusy(form, busy) {
    Array.from(form.elements).forEach(function (element) {
      element.disabled = busy;
    });
  }

  function statusText(status) {
    return msg("status." + status, status);
  }

  function accountId(account) {
    return account && account.id !== undefined && account.id !== null ? String(account.id) : "";
  }

  function rememberAccount(account) {
    const id = accountId(account);
    if (!id) {
      return;
    }
    accountStore.set(id, Object.assign({}, accountStore.get(id) || {}, account));
  }

  function updateEmptyState() {
    if (emptyState) {
      emptyState.hidden = accountsBody.querySelectorAll("tr").length > 0;
    }
  }

  function createCell(field, text, label) {
    const cell = document.createElement("td");
    cell.dataset.field = field;
    if (label) {
      cell.dataset.label = label;
    }
    cell.textContent = text || "";
    return cell;
  }

  function createCredentialCell(field, text, copyKind, label) {
    const cell = document.createElement("td");
    const wrapper = document.createElement("div");
    const value = document.createElement("button");
    const button = copyButton(copyKind, label);

    cell.dataset.field = field;
    wrapper.className = "credential-cell";
    value.type = "button";
    value.className = "credential-value";
    value.dataset.copy = copyKind;
    value.dataset.value = "";
    value.dataset.fullValue = text || "";
    value.textContent = text || "";
    value.title = text || "";
    value.setAttribute("aria-label", label);
    wrapper.appendChild(value);
    wrapper.appendChild(button);
    cell.appendChild(wrapper);
    return cell;
  }

  function renderRow(account) {
    const row = document.createElement("tr");
    row.dataset.accountId = account.id;
    row.appendChild(createCredentialCell("email", account.email, "email", msg("accounts.copy_email", "Copy email")));
    row.appendChild(
      createCredentialCell("password", account.password, "password", msg("accounts.copy_password", "Copy password"))
    );
    row.appendChild(createCell("copy_count", String(account.copy_count || 0), msg("accounts.copy_count", "Copies")));
    row.appendChild(createCell("status", statusText(account.status), msg("accounts.status", "Status")));

    const actions = document.createElement("td");
    const detailsButton = document.createElement("button");
    actions.className = "actions";
    actions.dataset.label = msg("accounts.details", "Details");
    detailsButton.type = "button";
    detailsButton.dataset.details = "";
    detailsButton.textContent = msg("accounts.details", "Details");
    actions.appendChild(detailsButton);
    row.appendChild(actions);
    updateRow(row, account);
    return row;
  }

  function copyButton(kind, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-button";
    button.dataset.copy = kind;
    button.textContent = "copy";
    button.setAttribute("aria-label", label);
    return button;
  }

  function setCredentialValue(row, field, text) {
    const value = row.querySelector('[data-field="' + field + '"] [data-value]');
    if (!value) {
      return;
    }
    value.textContent = text || "";
    value.title = text || "";
    value.dataset.fullValue = text || "";
  }

  function detailsAreOpen() {
    return accountDetailsDialog && !accountDetailsDialog.hidden;
  }

  function manualCopyIsOpen() {
    return manualCopyDialog && !manualCopyDialog.hidden;
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

  function updateRow(row, account) {
    rememberAccount(account);
    row.dataset.status = account.status;
    setCredentialValue(row, "email", account.email);
    setCredentialValue(row, "password", account.password);
    row.querySelector('[data-field="status"]').textContent = statusText(account.status);
    row.querySelector('[data-field="copy_count"]').textContent = String(account.copy_count || 0);
    if (
      accountDetailsDialog &&
      detailsAreOpen() &&
      accountDetailsDialog.dataset.accountId === accountId(account)
    ) {
      renderDetails(account);
    }
  }

  function detailValue(account, field) {
    if (field === "status") {
      return statusText(account.status);
    }
    if (field === "copy_count") {
      return String(account.copy_count || 0);
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
    accountDetailsDialog.querySelector("[data-details-close]")?.focus();
  }

  function closeDetails() {
    if (!accountDetailsDialog) {
      return;
    }
    accountDetailsDialog.hidden = true;
    document.body.classList.remove("details-open");
  }

  function upsertAccount(account, prepend) {
    let row = accountsBody.querySelector('[data-account-id="' + account.id + '"]');
    if (row) {
      updateRow(row, account);
    } else {
      row = renderRow(account);
      if (prepend && accountsBody.firstChild) {
        accountsBody.insertBefore(row, accountsBody.firstChild);
      } else {
        accountsBody.appendChild(row);
      }
    }
    updateEmptyState();
    if (account.status === "pending" || account.status === "running") {
      enqueuePoll(account.id);
    } else {
      stopPoll(account.id);
    }
  }

  function currentStatusFilter() {
    return new URLSearchParams(window.location.search).get("status") || "";
  }

  function shouldInsert(account) {
    const filter = currentStatusFilter();
    return !filter || filter === account.status;
  }

  function enqueuePoll(accountId) {
    if (activePolls.has(accountId) || pollQueue.includes(accountId)) {
      return;
    }
    pollQueue.push(accountId);
    drainPollQueue();
  }

  function drainPollQueue() {
    while (activePolls.size < maxPolls && pollQueue.length > 0) {
      const accountId = pollQueue.shift();
      pollAccount(accountId);
      const timer = window.setInterval(function () {
        pollAccount(accountId);
      }, pollIntervalMs);
      activePolls.set(accountId, timer);
    }
  }

  function stopPoll(accountId) {
    const timer = activePolls.get(accountId);
    if (timer) {
      window.clearInterval(timer);
      activePolls.delete(accountId);
      drainPollQueue();
    }
  }

  async function pollAccount(accountId) {
    try {
      const payload = await requestJson("/api/accounts/" + accountId, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (shouldInsert(payload.account)) {
        upsertAccount(payload.account, false);
      }
      if (payload.account.status === "success" || payload.account.status === "failed") {
        stopPoll(accountId);
      }
    } catch (error) {
      stopPoll(accountId);
      showMessage(error.message, true);
    }
  }

  async function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (error) {
        // Some embedded/mobile browsers expose the API but still deny writes.
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
      throw new Error(msg("accounts.copy_failed", "Copy failed."));
    }
  }

  async function copyCredential(text) {
    try {
      await copyText(text);
      return true;
    } catch (error) {
      openManualCopy(text);
      return false;
    }
  }

  document.querySelector("#single-register-form")?.addEventListener("submit", async function (event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(form, true);
    showMessage("", false);
    try {
      const payload = await requestJson("/api/register", {
        method: "POST",
        headers: headers(),
        body: "{}",
      });
      if (shouldInsert(payload.account)) {
        upsertAccount(payload.account, true);
      }
      showMessage(msg("accounts.register_started", "Registration started."), false);
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      setBusy(form, false);
    }
  });

  document.querySelector("#batch-register-form")?.addEventListener("submit", async function (event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(form, true);
    showMessage("", false);
    try {
      const payload = await requestJson("/api/register-batch", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ count: data.get("count") }),
      });
      payload.accounts.forEach(function (account) {
        if (shouldInsert(account)) {
          upsertAccount(account, true);
        } else {
          enqueuePoll(account.id);
        }
      });
      showMessage(
        msg("accounts.batch_started", "Batch registration started.", {
          count: payload.accounts.length,
        }),
        false
      );
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      setBusy(form, false);
    }
  });

  accountsBody.addEventListener("click", async function (event) {
    const detailsButton = event.target.closest("button[data-details]");
    if (detailsButton) {
      openDetails(detailsButton.closest("tr"));
      return;
    }

    const button = event.target.closest("[data-copy]");
    if (!button) {
      return;
    }
    const row = button.closest("tr");
    const kind = button.dataset.copy;
    const account = accountStore.get(row.dataset.accountId) || {};
    const field = row.querySelector('[data-field="' + (kind === "email" ? "email" : "password") + '"] [data-value]');
    const text = account[kind] || (field ? field.dataset.fullValue || field.textContent : "");
    button.disabled = true;
    try {
      const copied = await copyCredential(text);
      if (copied && kind === "email") {
        const payload = await requestJson(
          "/api/accounts/" + row.dataset.accountId + "/copy-account",
          { method: "POST", headers: headers(), body: "{}" }
        );
        updateRow(row, payload.account);
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
      button.disabled = false;
    }
  });

  accountDetailsDialog?.addEventListener("click", function (event) {
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
    if (event.key === "Escape" && detailsAreOpen()) {
      closeDetails();
    }
    if (event.key === "Escape" && manualCopyIsOpen()) {
      closeManualCopy();
    }
  });

  (config.accounts || []).forEach(function (account) {
    rememberAccount(account);
    if (account.status === "pending" || account.status === "running") {
      enqueuePoll(account.id);
    }
  });
  updateEmptyState();
})();
