const state = { selectedRunId: null, pendingAction: null };

/* ---- helpers ---- */

async function api(path, options) {
  if (!options) options = {};
  var headers = { "Content-Type": "application/json" };
  if (options.headers) {
    var keys = Object.keys(options.headers);
    for (var i = 0; i < keys.length; i++) {
      headers[keys[i]] = options.headers[keys[i]];
    }
  }
  var fetchOpts = {
    headers: headers,
    method: options.method || "GET",
    body: options.body || undefined,
  };
  var response = await fetch(path, fetchOpts);
  var data = await response.json();
  if (!response.ok) throw new Error(data.detail || ("HTTP " + response.status));
  return data;
}

function escapeHtml(value) {
  var text = String(value ?? "");
  var node = document.createTextNode(text);
  var div = document.createElement("div");
  div.appendChild(node);
  return div.innerHTML;
}

function statusBadge(status) {
  return '<span class="status ' + escapeHtml(status) + '">' + escapeHtml(status) + '</span>';
}

function isGuidanceRequired(action) {
  return action === "revise";
}

function shouldShowGuidanceField(action) {
  return action === "revise" || action === "reject";
}

/* ---- decision UI ---- */

function resetDecisionUI() {
  state.pendingAction = null;
  var confirmArea = document.querySelector("#decision-confirm-area");
  if (confirmArea) confirmArea.classList.add("hidden");
  var guidanceField = document.querySelector("#decision-guidance");
  if (guidanceField) guidanceField.value = "";
  var errorEl = document.querySelector("#decision-error");
  if (errorEl) errorEl.textContent = "";
  var buttons = document.querySelectorAll("#decision-box button");
  buttons.forEach(function (b) { b.disabled = false; });
}

function showConfirmArea(action) {
  state.pendingAction = action;
  var confirmArea = document.querySelector("#decision-confirm-area");
  var confirmMsg = document.querySelector("#decision-confirm-message");
  var guidanceWrap = document.querySelector("#decision-guidance-wrap");
  var guidanceField = document.querySelector("#decision-guidance");

  if (shouldShowGuidanceField(action)) {
    guidanceWrap.classList.remove("hidden");
    var labelText = action === "revise"
      ? "Anweisung f\u00fcr \u00dcberarbeitung (erforderlich):"
      : "Begr\u00fcndung (optional):";
    guidanceWrap.querySelector("label").textContent = labelText;
    guidanceField.placeholder = action === "revise"
      ? "Bitte geben Sie eine Anweisung f\u00fcr die \u00dcberarbeitung ein."
      : "Begr\u00fcndung (optional)";
    guidanceField.value = "";
  } else {
    guidanceWrap.classList.add("hidden");
  }

  var msg = action === "approve" ? "Freigabe best\u00e4tigen?"
    : action === "revise" ? "\u00dcberarbeitung anfordern?"
    : "Ablehnung best\u00e4tigen?";
  confirmMsg.textContent = msg;

  var btnLabel = action === "approve" ? "Best\u00e4tigen"
    : action === "revise" ? "\u00dcberarbeitung senden"
    : "Ablehnung senden";
  document.querySelector("#decision-confirm-action").textContent = btnLabel;

  document.querySelector("#decision-error").textContent = "";
  confirmArea.classList.remove("hidden");
}

async function confirmDecision() {
  var action = state.pendingAction;
  if (!action || !state.selectedRunId) return;

  var errorEl = document.querySelector("#decision-error");
  var guidanceField = document.querySelector("#decision-guidance");
  var guidance = guidanceField ? guidanceField.value : "";

  if (isGuidanceRequired(action) && !guidance.trim()) {
    errorEl.textContent = "Bei \u00dcberarbeitung ist eine Anweisung erforderlich.";
    return;
  }

  var buttons = document.querySelectorAll("#decision-box button, #decision-confirm-area button");
  buttons.forEach(function (b) { b.disabled = true; });
  try {
    await api("/api/runs/" + state.selectedRunId + "/decision", {
      method: "POST",
      body: JSON.stringify({ action: action, guidance: guidance }),
    });
    resetDecisionUI();
    await loadRuns();
    await showRun(state.selectedRunId);
  } catch (error) {
    errorEl.textContent = error.message;
  } finally {
    buttons.forEach(function (b) { b.disabled = false; });
  }
}

function cancelDecision() {
  resetDecisionUI();
}

/* ---- system data ---- */

async function loadSystem() {
  var info = await api("/api/system");
  var mafBadge = info.maf_installed ? "ok" : "warn";
  var mafText = "MAF " + (info.maf_version || "nicht installiert");
  var provBadge = info.provider_configured ? "ok" : "warn";
  var provText = "Provider " + (info.provider_configured ? "konfiguriert" : "nicht konfiguriert");
  var badges = [
    '<span class="badge ' + mafBadge + '">' + mafText + '</span>',
    '<span class="badge ' + provBadge + '">' + provText + '</span>',
    '<span class="badge">Modell ' + escapeHtml(info.provider_model) + '</span>',
  ];
  document.querySelector("#system-badges").innerHTML = badges.join("");
}

async function loadConcepts() {
  var concepts = await api("/api/concepts");
  var html = concepts.map(function (c) {
    return '<article class="concept">'
      + '<span class="layer">' + escapeHtml(c.layer) + '</span>'
      + '<h3>' + escapeHtml(c.title) + '</h3>'
      + '<p>' + escapeHtml(c.explanation) + '</p>'
      + '<p><strong>Im Labor:</strong> ' + escapeHtml(c.visible_in_platform) + '</p>'
      + '</article>';
  }).join("");
  document.querySelector("#concept-grid").innerHTML = html;
}

/* ---- runs ---- */

async function loadRuns(selectNewest) {
  if (selectNewest === undefined) selectNewest = false;
  var runs = await api("/api/runs");
  var list = document.querySelector("#runs-list");
  if (!runs.length) {
    list.innerHTML = '<div class="empty">Noch kein Workflow-Lauf vorhanden.</div>';
    return;
  }
  var html = runs.map(function (run) {
    var amount = Number(run.amount_eur).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
    var date = new Date(run.updated_at).toLocaleString("de-DE");
    return '<button class="run-row" data-run-id="' + escapeHtml(run.id) + '">'
      + '<strong>' + escapeHtml(run.invoice_number) + ' \u00b7 ' + escapeHtml(run.customer_name) + '</strong>'
      + statusBadge(run.status)
      + '<small>' + amount + ' \u00b7 ' + run.days_overdue + ' Tage \u00b7 ' + escapeHtml(run.mode) + '</small>'
      + '<small>' + date + '</small>'
      + '</button>';
  }).join("");
  list.innerHTML = html;
  list.querySelectorAll("[data-run-id]").forEach(function (button) {
    button.addEventListener("click", function () { showRun(button.dataset.runId); });
  });
  if (selectNewest) await showRun(runs[0].id);
}

async function showRun(runId) {
  resetDecisionUI();
  var run = await api("/api/runs/" + runId);
  state.selectedRunId = runId;
  document.querySelector("#run-detail-panel").classList.remove("hidden");
  document.querySelector("#detail-title").textContent = run.invoice_number + " \u00b7 " + run.customer_name;
  document.querySelector("#detail-status").innerHTML = statusBadge(run.status);
  document.querySelector("#detail-mode").textContent = run.mode;
  document.querySelector("#detail-risk").textContent = run.risk_level + ": " + (run.risk_reasons || []).join("; ");
  document.querySelector("#detail-checkpoint").textContent = run.checkpoint_id || "\u2013";
  document.querySelector("#detail-request").textContent = run.request_id || "\u2013";
  document.querySelector("#recommendation").textContent = run.recommendation || run.error || "Noch keine Empfehlung vorhanden.";

  var decisionBox = document.querySelector("#decision-box");
  if (decisionBox) decisionBox.classList.toggle("hidden", run.status !== "awaiting_human");
  var outputWrap = document.querySelector("#final-output-wrap");
  if (outputWrap) outputWrap.classList.toggle("hidden", !run.output);
  var finalOut = document.querySelector("#final-output");
  if (finalOut) finalOut.textContent = run.output || "";

  var events = run.events || [];
  var eventsHtml = events.map(function (event) {
    var time = new Date(event.created_at).toLocaleTimeString("de-DE");
    return '<article class="timeline-item">'
      + '<strong>' + escapeHtml(event.source || "") + ' \u00b7 ' + escapeHtml(event.event_type || "") + '</strong>'
      + '<small>' + time + ' \u00b7 ' + escapeHtml(event.phase || "") + '</small>'
      + '<p>' + escapeHtml(event.summary || "") + '</p>'
      + '</article>';
  }).join("");
  var tl = document.querySelector("#event-timeline");
  if (tl) tl.innerHTML = eventsHtml || '<div class="empty">Keine Events vorhanden.</div>';

  var cps = run.checkpoints || [];
  var cpHtml = cps.map(function (cp) {
    return '<div class="checkpoint">'
      + '<strong>' + escapeHtml(cp.checkpoint_id || "") + '</strong>'
      + '<span title="' + escapeHtml(cp.storage_path || "") + '">' + escapeHtml(cp.storage_path || "") + '</span>'
      + '<span>' + escapeHtml(cp.status || "") + '</span>'
      + '</div>';
  }).join("");
  var cl = document.querySelector("#checkpoint-list");
  if (cl) cl.innerHTML = cpHtml || '<div class="empty">Noch kein Checkpoint gespeichert.</div>';

  var panel = document.querySelector("#run-detail-panel");
  if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---- form submit ---- */

async function submitRun(event) {
  event.preventDefault();
  resetDecisionUI();
  var form = event.currentTarget;
  var button = form.querySelector("button[type=submit]");
  var message = document.querySelector("#form-message");
  button.disabled = true;
  message.textContent = "Workflow wird ausgef\u00fchrt \u2026";
  var fd = new FormData(form);
  var values = {};
  var pairs = fd.entries();
  for (var pair = pairs.next(); !pair.done; pair = pairs.next()) {
    values[pair.value[0]] = pair.value[1];
  }
  var payload = {
    customer_name: values.customer_name,
    invoice_number: values.invoice_number,
    amount_eur: Number(values.amount_eur),
    days_overdue: Number(values.days_overdue),
    context: values.context,
    mode: values.mode,
  };
  try {
    var run = await api("/api/runs", { method: "POST", body: JSON.stringify(payload) });
    message.textContent = run.status === "failed" ? "Fehlgeschlagen: " + run.error : "Lauf wurde gespeichert.";
    await loadRuns();
    await showRun(run.id);
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

/* ---- init ---- */

function init() {
  var form = document.querySelector("#run-form");
  if (form) form.addEventListener("submit", submitRun);

  var modeSelect = document.querySelector("#run-form select[name=mode]");
  if (modeSelect) modeSelect.addEventListener("change", resetDecisionUI);

  var refresh = document.querySelector("#refresh-runs");
  if (refresh) refresh.addEventListener("click", function () { loadRuns(); });

  document.querySelectorAll("#decision-box [data-action]").forEach(function (button) {
    button.addEventListener("click", function () { showConfirmArea(button.dataset.action); });
  });

  var confirmBtn = document.querySelector("#decision-confirm");
  if (confirmBtn) confirmBtn.addEventListener("click", confirmDecision);

  var cancelBtn = document.querySelector("#decision-cancel");
  if (cancelBtn) cancelBtn.addEventListener("click", cancelDecision);

  Promise.all([loadSystem(), loadConcepts(), loadRuns()]).catch(function (error) {
    var msg = document.querySelector("#form-message");
    if (msg) msg.textContent = "Initialisierung fehlgeschlagen: " + error.message;
  });
}

window.addEventListener("DOMContentLoaded", init);
