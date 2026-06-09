(function () {
  "use strict";

  const config = window.APP_CONFIG || {};
  const messages = config.messages || {};
  const accountsBody = document.querySelector("#accounts-body");
  const emptyState = document.querySelector("#empty-state");
  const flashMessage = document.querySelector("#flash-message");
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

  function updateEmptyState() {
    if (emptyState) {
      emptyState.hidden = accountsBody.querySelectorAll("tr").length > 0;
    }
  }

  function createCell(field, text) {
    const cell = document.createElement("td");
    cell.dataset.field = field;
    cell.textContent = text || "";
    return cell;
  }

  function renderRow(account) {
    const row = document.createElement("tr");
    row.dataset.accountId = account.id;
    row.appendChild(createCell("email", account.email));
    row.appendChild(createCell("password", account.password));
    row.appendChild(createCell("status", statusText(account.status)));
    row.appendChild(createCell("error_message", account.error_message || ""));
    row.appendChild(createCell("copy_count", String(account.copy_count || 0)));
    row.appendChild(createCell("last_copied_at", account.last_copied_at || ""));
    row.appendChild(createCell("created_at", account.created_at || ""));
    row.appendChild(createCell("updated_at", account.updated_at || ""));

    const actions = document.createElement("td");
    actions.className = "actions";
    actions.appendChild(copyButton("email", msg("accounts.copy_email", "Copy email")));
    actions.appendChild(copyButton("password", msg("accounts.copy_password", "Copy password")));
    row.appendChild(actions);
    updateRow(row, account);
    return row;
  }

  function copyButton(kind, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.copy = kind;
    button.textContent = label;
    return button;
  }

  function updateRow(row, account) {
    row.dataset.status = account.status;
    row.querySelector('[data-field="email"]').textContent = account.email || "";
    row.querySelector('[data-field="password"]').textContent = account.password || "";
    row.querySelector('[data-field="status"]').textContent = statusText(account.status);
    row.querySelector('[data-field="error_message"]').textContent = account.error_message || "";
    row.querySelector('[data-field="copy_count"]').textContent = String(account.copy_count || 0);
    row.querySelector('[data-field="last_copied_at"]').textContent = account.last_copied_at || "";
    row.querySelector('[data-field="created_at"]').textContent = account.created_at || "";
    row.querySelector('[data-field="updated_at"]').textContent = account.updated_at || "";
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
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
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
    const button = event.target.closest("button[data-copy]");
    if (!button) {
      return;
    }
    const row = button.closest("tr");
    const kind = button.dataset.copy;
    const field = row.querySelector('[data-field="' + (kind === "email" ? "email" : "password") + '"]');
    const text = field ? field.textContent : "";
    button.disabled = true;
    try {
      await copyText(text);
      if (kind === "email") {
        const payload = await requestJson(
          "/api/accounts/" + row.dataset.accountId + "/copy-account",
          { method: "POST", headers: headers(), body: "{}" }
        );
        updateRow(row, payload.account);
      }
      showMessage(msg("accounts.copy_success", "Copied."), false);
    } catch (error) {
      showMessage(error.message || msg("accounts.copy_failed", "Copy failed."), true);
    } finally {
      button.disabled = false;
    }
  });

  (config.accounts || []).forEach(function (account) {
    if (account.status === "pending" || account.status === "running") {
      enqueuePoll(account.id);
    }
  });
  updateEmptyState();
})();
