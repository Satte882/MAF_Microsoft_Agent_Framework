const state = { selectedRunId: null };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusBadge(status) {
  return `<span class="status ${escapeHtml(status)}">${escapeHtml(status)}</span>`;
}

async function loadSystem() {
  const info = await api("/api/system");
  const badges = [
    `<span class="badge ${info.maf_installed ? "ok" : "warn"}">MAF ${info.maf_version || "nicht installiert"}</span>`,
    `<span class="badge ${info.provider_configured ? "ok" : "warn"}">Provider ${info.provider_configured ? "konfiguriert" : "nicht konfiguriert"}</span>`,
    `<span class="badge">Modell ${escapeHtml(info.provider_model)}</span>`,
  ];
  document.querySelector("#system-badges").innerHTML = badges.join("");
}

async function loadConcepts() {
  const concepts = await api("/api/concepts");
  document.querySelector("#concept-grid").innerHTML = concepts.map((concept) => `
    <article class="concept">
      <span class="layer">${escapeHtml(concept.layer)}</span>
      <h3>${escapeHtml(concept.title)}</h3>
      <p>${escapeHtml(concept.explanation)}</p>
      <p><strong>Im Labor:</strong> ${escapeHtml(concept.visible_in_platform)}</p>
    </article>
  `).join("");
}

async function loadRuns(selectNewest = false) {
  const runs = await api("/api/runs");
  const list = document.querySelector("#runs-list");
  if (!runs.length) {
    list.innerHTML = '<div class="empty">Noch kein Workflow-Lauf vorhanden.</div>';
    return;
  }
  list.innerHTML = runs.map((run) => `
    <button class="run-row" data-run-id="${escapeHtml(run.id)}">
      <strong>${escapeHtml(run.invoice_number)} · ${escapeHtml(run.customer_name)}</strong>
      ${statusBadge(run.status)}
      <small>${Number(run.amount_eur).toLocaleString("de-DE", { style: "currency", currency: "EUR" })} · ${run.days_overdue} Tage · ${escapeHtml(run.mode)}</small>
      <small>${new Date(run.updated_at).toLocaleString("de-DE")}</small>
    </button>
  `).join("");
  list.querySelectorAll("[data-run-id]").forEach((button) => {
    button.addEventListener("click", () => showRun(button.dataset.runId));
  });
  if (selectNewest) await showRun(runs[0].id);
}

async function showRun(runId) {
  const run = await api(`/api/runs/${runId}`);
  state.selectedRunId = runId;
  document.querySelector("#run-detail-panel").classList.remove("hidden");
  document.querySelector("#detail-title").textContent = `${run.invoice_number} · ${run.customer_name}`;
  document.querySelector("#detail-status").innerHTML = statusBadge(run.status);
  document.querySelector("#detail-mode").textContent = run.mode;
  document.querySelector("#detail-risk").textContent = `${run.risk_level}: ${run.risk_reasons.join("; ")}`;
  document.querySelector("#detail-checkpoint").textContent = run.checkpoint_id || "–";
  document.querySelector("#detail-request").textContent = run.request_id || "–";
  document.querySelector("#recommendation").textContent = run.recommendation || run.error || "Noch keine Empfehlung vorhanden.";

  const decisionBox = document.querySelector("#decision-box");
  decisionBox.classList.toggle("hidden", run.status !== "awaiting_human");
  const outputWrap = document.querySelector("#final-output-wrap");
  outputWrap.classList.toggle("hidden", !run.output);
  document.querySelector("#final-output").textContent = run.output || "";

  document.querySelector("#event-timeline").innerHTML = run.events.map((event) => `
    <article class="timeline-item">
      <strong>${escapeHtml(event.source)} · ${escapeHtml(event.event_type)}</strong>
      <small>${new Date(event.created_at).toLocaleTimeString("de-DE")} · ${escapeHtml(event.phase)}</small>
      <p>${escapeHtml(event.summary)}</p>
    </article>
  `).join("") || '<div class="empty">Keine Events vorhanden.</div>';

  document.querySelector("#checkpoint-list").innerHTML = run.checkpoints.map((checkpoint) => `
    <div class="checkpoint">
      <strong>${escapeHtml(checkpoint.checkpoint_id)}</strong>
      <span title="${escapeHtml(checkpoint.storage_path)}">${escapeHtml(checkpoint.storage_path)}</span>
      <span>${escapeHtml(checkpoint.status)}</span>
    </div>
  `).join("") || '<div class="empty">Noch kein Checkpoint gespeichert.</div>';

  document.querySelector("#run-detail-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function submitRun(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const message = document.querySelector("#form-message");
  button.disabled = true;
  message.textContent = "Workflow wird ausgeführt …";
  const values = Object.fromEntries(new FormData(form).entries());
  const payload = {
    ...values,
    amount_eur: Number(values.amount_eur),
    days_overdue: Number(values.days_overdue),
  };
  try {
    const run = await api("/api/runs", { method: "POST", body: JSON.stringify(payload) });
    message.textContent = run.status === "failed" ? `Fehlgeschlagen: ${run.error}` : "Lauf wurde gespeichert.";
    await loadRuns();
    await showRun(run.id);
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function submitDecision(action) {
  if (!state.selectedRunId) return;
  const buttons = document.querySelectorAll("#decision-box button");
  buttons.forEach((button) => { button.disabled = true; });
  try {
    const guidance = document.querySelector("#decision-guidance").value;
    await api(`/api/runs/${state.selectedRunId}/decision`, {
      method: "POST",
      body: JSON.stringify({ action, guidance }),
    });
    document.querySelector("#decision-guidance").value = "";
    await loadRuns();
    await showRun(state.selectedRunId);
  } catch (error) {
    alert(error.message);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  document.querySelector("#run-form").addEventListener("submit", submitRun);
  document.querySelector("#refresh-runs").addEventListener("click", () => loadRuns());
  document.querySelectorAll("#decision-box [data-action]").forEach((button) => {
    button.addEventListener("click", () => submitDecision(button.dataset.action));
  });
  try {
    await Promise.all([loadSystem(), loadConcepts(), loadRuns()]);
  } catch (error) {
    document.querySelector("#form-message").textContent = `Initialisierung fehlgeschlagen: ${error.message}`;
  }
});
