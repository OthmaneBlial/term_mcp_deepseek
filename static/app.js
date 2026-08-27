(() => {
  "use strict";

  const TOKEN_KEY = "term-mcp-auth";
  const MODERN_VERSION = "2026-07-28";
  const META = {
    "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {
      name: "term-mcp-mission-control",
      version: "1.0.0",
    },
  };

  const byId = (id) => document.getElementById(id);
  const ui = {
    authGate: byId("authGate"),
    authForm: byId("authForm"),
    tokenInput: byId("tokenInput"),
    authError: byId("authError"),
    connectionChip: byId("connectionChip"),
    connectionLabel: byId("connectionLabel"),
    modeChip: byId("modeChip"),
    modelChip: byId("modelChip"),
    newSessionButton: byId("newSessionButton"),
    lockButton: byId("lockButton"),
    workspaceValue: byId("workspaceValue"),
    sessionValue: byId("sessionValue"),
    retentionValue: byId("retentionValue"),
    networkValue: byId("networkValue"),
    scenarioList: byId("scenarioList"),
    commandForm: byId("commandForm"),
    commandInput: byId("commandInput"),
    cwdInput: byId("cwdInput"),
    planButton: byId("planButton"),
    executionStrip: byId("executionStrip"),
    executionState: byId("executionState"),
    executionDetail: byId("executionDetail"),
    pauseButton: byId("pauseButton"),
    resumeButton: byId("resumeButton"),
    cancelButton: byId("cancelButton"),
    notice: byId("notice"),
    noticeText: byId("noticeText"),
    noticeClose: byId("noticeClose"),
    eventCounter: byId("eventCounter"),
    emptyLedger: byId("emptyLedger"),
    planLedger: byId("planLedger"),
    planTemplate: byId("planTemplate"),
    advisorForm: byId("advisorForm"),
    advisorInput: byId("advisorInput"),
    advisorButton: byId("advisorButton"),
    advisorResponse: byId("advisorResponse"),
    advisorText: byId("advisorText"),
    receiptSeal: byId("receiptSeal"),
    importReceiptButton: byId("importReceiptButton"),
    exportReceiptButton: byId("exportReceiptButton"),
    copyReceiptButton: byId("copyReceiptButton"),
    receiptFileInput: byId("receiptFileInput"),
    receiptEmpty: byId("receiptEmpty"),
    receiptPaper: byId("receiptPaper"),
    receiptStatus: byId("receiptStatus"),
    receiptDuration: byId("receiptDuration"),
    receiptId: byId("receiptId"),
    receiptSession: byId("receiptSession"),
    receiptPermission: byId("receiptPermission"),
    receiptExit: byId("receiptExit"),
    receiptCommand: byId("receiptCommand"),
    receiptStdout: byId("receiptStdout"),
    receiptStderr: byId("receiptStderr"),
    receiptSignature: byId("receiptSignature"),
  };

  const state = {
    token: sessionStorage.getItem(TOKEN_KEY) || "",
    sessionId: "",
    streamController: null,
    eventCount: 0,
    requestId: 0,
    plans: new Map(),
    currentReceipt: null,
    activePlanId: "",
  };

  function authHeaders(extra = {}) {
    return {
      Authorization: `Bearer ${state.token}`,
      ...extra,
    };
  }

  function setConnection(status, label) {
    ui.connectionChip.dataset.state = status;
    ui.connectionLabel.textContent = label;
  }

  function notify(message, kind = "info") {
    ui.noticeText.textContent = message;
    ui.notice.dataset.kind = kind;
    ui.notice.hidden = false;
  }

  function clearNotice() {
    ui.notice.hidden = true;
    ui.noticeText.textContent = "";
    delete ui.notice.dataset.kind;
  }

  function readableError(error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/unauthorized/i.test(message)) {
      return "Authentication failed. Check the bearer token printed by term-mcp serve.";
    }
    if (/rate_limit/i.test(message)) {
      return "The local request limit was reached. Wait a minute, then try again.";
    }
    if (/unknown or expired session/i.test(message)) {
      return "This session expired. Create a new session and build the plan again.";
    }
    if (/requires explicit approval/i.test(message)) {
      return "This plan needs explicit approval before it can execute.";
    }
    return message || "The local server returned an unexpected error.";
  }

  async function request(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });
    const type = response.headers.get("content-type") || "";
    const payload = type.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      const detail = payload?.error?.message || payload?.error || `HTTP ${response.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return payload;
  }

  async function tool(name, argumentsPayload) {
    state.requestId += 1;
    const params = { name, arguments: argumentsPayload, _meta: META };
    const response = await request("/mcp", {
      method: "POST",
      headers: {
        Accept: "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": MODERN_VERSION,
        "Mcp-Method": "tools/call",
        "Mcp-Name": name,
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: state.requestId,
        method: "tools/call",
        params,
      }),
    });
    if (response.error) {
      throw new Error(response.error.message || "MCP request failed");
    }
    const result = response.result || {};
    const value = result.structuredContent || {};
    if (result.isError && !value.schema_version) {
      throw new Error(value.message || result.content?.[0]?.text || "Tool execution failed");
    }
    return value;
  }

  function resetWorkspace() {
    state.plans.clear();
    state.currentReceipt = null;
    state.activePlanId = "";
    state.eventCount = 0;
    ui.planLedger.replaceChildren();
    ui.emptyLedger.hidden = false;
    ui.eventCounter.textContent = "0 events";
    ui.receiptPaper.hidden = true;
    ui.receiptEmpty.hidden = false;
    ui.receiptSeal.textContent = "EMPTY";
    delete ui.receiptSeal.dataset.state;
    ui.exportReceiptButton.disabled = true;
    ui.copyReceiptButton.disabled = true;
    setExecution("idle", "Waiting for a plan", "No command has crossed the execution boundary.");
    setControls();
  }

  function formatDuration(seconds) {
    if (!Number.isFinite(Number(seconds))) return "—";
    const value = Number(seconds);
    return value >= 60 ? `${Math.round(value / 60)} min` : `${value} sec`;
  }

  function compactId(value) {
    if (!value) return "—";
    return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
  }

  async function connect() {
    setConnection("connecting", "Connecting");
    ui.authError.textContent = "";
    const info = await request("/mcp/info");
    const created = await request("/sessions", { method: "POST" });
    state.sessionId = created.session_id;
    ui.workspaceValue.textContent = info.workspace;
    ui.sessionValue.textContent = compactId(state.sessionId);
    ui.sessionValue.title = state.sessionId;
    ui.retentionValue.textContent = formatDuration(info.limits?.session_timeout_seconds);
    ui.networkValue.textContent = info.network_allowed ? "Allowed by policy" : "Denied by default";
    ui.modeChip.textContent = `MODE ${String(info.approval_mode || "—").toUpperCase()}`;
    const modelState = info.model?.available ? info.model.model : "UNAVAILABLE";
    ui.modelChip.textContent = `MODEL ${String(modelState).toUpperCase()}`;
    ui.authGate.hidden = true;
    setConnection("online", "Local / ready");
    resetWorkspace();
    startStream();
    ui.commandInput.focus();
  }

  async function closeSession() {
    state.streamController?.abort();
    state.streamController = null;
    if (!state.sessionId || !state.token) return;
    const closingSession = state.sessionId;
    state.sessionId = "";
    try {
      await request(`/sessions/${encodeURIComponent(closingSession)}`, { method: "DELETE" });
    } catch (_error) {
      // Closing is best-effort when the local server or session is already gone.
    }
  }

  async function lock() {
    await closeSession();
    sessionStorage.removeItem(TOKEN_KEY);
    state.token = "";
    resetWorkspace();
    ui.workspaceValue.textContent = "Authenticate to reveal";
    ui.sessionValue.textContent = "—";
    ui.retentionValue.textContent = "—";
    ui.networkValue.textContent = "—";
    ui.modeChip.textContent = "MODE —";
    ui.modelChip.textContent = "MODEL —";
    setConnection("offline", "Locked");
    ui.authGate.hidden = false;
    ui.tokenInput.value = "";
    ui.tokenInput.focus();
  }

  async function newSession() {
    ui.newSessionButton.disabled = true;
    try {
      await closeSession();
      const created = await request("/sessions", { method: "POST" });
      state.sessionId = created.session_id;
      ui.sessionValue.textContent = compactId(state.sessionId);
      ui.sessionValue.title = state.sessionId;
      resetWorkspace();
      startStream();
      notify("A fresh isolated session is ready.");
    } catch (error) {
      notify(readableError(error), "error");
    } finally {
      ui.newSessionButton.disabled = false;
    }
  }

  function startStream() {
    state.streamController?.abort();
    const controller = new AbortController();
    state.streamController = controller;
    void consumeStream(controller);
  }

  async function consumeStream(controller) {
    try {
      const response = await fetch(`/stream?session_id=${encodeURIComponent(state.sessionId)}`, {
        headers: authHeaders({ Accept: "text/event-stream" }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        throw new Error(`Event stream unavailable (HTTP ${response.status})`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          handleSseBlock(block);
          boundary = buffer.indexOf("\n\n");
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        notify(readableError(error), "error");
      }
    }
  }

  function handleSseBlock(block) {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    try {
      const payload = JSON.parse(data);
      if (payload.ok || payload.ts) return;
      state.eventCount += 1;
      ui.eventCounter.textContent = `${state.eventCount} event${state.eventCount === 1 ? "" : "s"}`;
      applyEvent(payload);
    } catch (_error) {
      notify("The event stream sent malformed data; execution state may need a refresh.", "error");
    }
  }

  function applyEvent(event) {
    if (event.plan) renderPlan(event.plan);
    if (event.type === "command_start") {
      state.activePlanId = event.plan.id;
      setExecution("running", "Command running", event.plan.command);
      setControls("running");
    } else if (event.type === "command_paused") {
      setExecution("paused", "Command paused", "The process group is stopped and can be resumed or cancelled.");
      setControls("paused");
    } else if (event.type === "command_resumed") {
      setExecution("running", "Command resumed", event.plan.command);
      setControls("running");
    } else if (event.receipt) {
      state.activePlanId = "";
      renderReceipt(event.receipt, { schema_valid: true, signature_valid: true });
      setExecution(
        event.receipt.status,
        `Command ${String(event.receipt.status).replace("_", " ")}`,
        `${event.receipt.duration_ms} ms · receipt ${compactId(event.receipt.id)}`,
      );
      setControls();
      const stored = state.plans.get(event.receipt.plan_id);
      if (stored) renderPlan({ ...stored, status: event.receipt.status });
    }
  }

  function setExecution(status, title, detail) {
    ui.executionStrip.dataset.state = status;
    ui.executionState.textContent = title;
    ui.executionDetail.textContent = detail;
  }

  function setControls(mode = "idle") {
    ui.pauseButton.disabled = mode !== "running";
    ui.resumeButton.disabled = mode !== "paused";
    ui.cancelButton.disabled = mode !== "running" && mode !== "paused";
  }

  function renderPlan(plan) {
    state.plans.set(plan.id, plan);
    ui.emptyLedger.hidden = true;
    let card = ui.planLedger.querySelector(`[data-plan-id="${CSS.escape(plan.id)}"]`);
    if (!card) {
      const fragment = ui.planTemplate.content.cloneNode(true);
      card = fragment.querySelector(".plan-card");
      card.dataset.planId = plan.id;
      ui.planLedger.prepend(fragment);
    }
    card.querySelector(".plan-index").textContent = `PLAN ${state.plans.size.toString().padStart(2, "0")}`;
    card.querySelector(".plan-state").textContent = String(plan.status).toUpperCase();
    const risk = plan.policy?.risk || plan.preview?.risk || "unknown";
    const riskBadge = card.querySelector(".risk-badge");
    riskBadge.dataset.risk = risk;
    riskBadge.textContent = `${String(risk).toUpperCase()} RISK`;
    card.querySelector(".plan-command").textContent = plan.command;
    card.querySelector(".plan-cwd").textContent = plan.cwd || "Workspace root";
    const touched = plan.preview?.files_potentially_touched || [];
    card.querySelector(".plan-files").textContent = touched.length ? touched.join(", ") : "None predicted";
    card.querySelector(".plan-network").textContent = plan.preview?.network_requested ? "Requested" : "Not requested";
    card.querySelector(".plan-timeout").textContent = `${plan.limits?.timeout_seconds ?? "—"} sec / ${formatBytes(plan.limits?.max_output_bytes)}`;
    const reasons = card.querySelector(".plan-reasons");
    reasons.replaceChildren();
    (plan.policy?.reasons || ["No policy explanation returned."]).forEach((reason) => {
      const item = document.createElement("li");
      item.textContent = reason;
      reasons.append(item);
    });

    const approve = card.querySelector(".approve-plan");
    const execute = card.querySelector(".execute-plan");
    const retry = card.querySelector(".retry-plan");
    const terminal = ["succeeded", "failed", "cancelled", "timed_out", "blocked"].includes(plan.status);
    approve.hidden = !plan.policy?.requires_approval;
    approve.disabled = plan.status !== "planned" || !plan.policy?.allowed;
    approve.textContent = plan.status === "approved" ? "Approved" : "Approve plan";
    execute.disabled =
      !plan.policy?.allowed ||
      terminal ||
      plan.status === "running" ||
      plan.status === "paused" ||
      (plan.policy?.requires_approval && plan.status !== "approved");
    retry.disabled = plan.status === "running" || plan.status === "paused";
    card.querySelector(".copy-command").onclick = () => copyText(plan.command, "Command copied.");
    approve.onclick = () => approvePlan(plan.id);
    execute.onclick = () => executePlan(plan.id);
    retry.onclick = () => retryPlan(plan.id);
    return card;
  }

  function formatBytes(bytes) {
    const value = Number(bytes);
    if (!Number.isFinite(value)) return "—";
    if (value >= 1_048_576) return `${(value / 1_048_576).toFixed(value % 1_048_576 ? 1 : 0)} MiB`;
    return `${Math.round(value / 1024)} KiB`;
  }

  async function buildPlan(event) {
    event?.preventDefault();
    if (!state.sessionId) {
      notify("Authenticate and create a session before building a plan.", "error");
      return;
    }
    const command = ui.commandInput.value.trim();
    if (!command) return;
    ui.planButton.disabled = true;
    ui.planButton.querySelector("span").textContent = "Planning…";
    clearNotice();
    try {
      const args = { session_id: state.sessionId, command };
      const cwd = ui.cwdInput.value.trim();
      if (cwd) args.cwd = cwd;
      const plan = await tool("terminal_plan", args);
      renderPlan(plan).scrollIntoView({ behavior: "smooth", block: "nearest" });
      setExecution(
        plan.status,
        plan.status === "blocked" ? "Plan blocked" : "Plan ready",
        plan.status === "blocked"
          ? "Policy denied this command before execution."
          : "Review risk, scope, and limits before you approve or execute.",
      );
      notify(plan.status === "blocked" ? "Policy blocked the plan. Read its reasons below." : "Plan created. Nothing has executed.", plan.status === "blocked" ? "error" : "info");
    } catch (error) {
      notify(readableError(error), "error");
    } finally {
      ui.planButton.disabled = false;
      ui.planButton.querySelector("span").textContent = "Build plan";
    }
  }

  async function approvePlan(planId) {
    try {
      const plan = await tool("terminal_approve", { session_id: state.sessionId, plan_id: planId });
      renderPlan(plan);
      notify("Plan approved. It has still not executed.");
    } catch (error) {
      notify(readableError(error), "error");
    }
  }

  async function executePlan(planId) {
    state.activePlanId = planId;
    setExecution("running", "Starting command", "Waiting for the bounded process to start…");
    setControls("running");
    lockPlanActions(planId, true);
    clearNotice();
    try {
      const receipt = await tool("terminal_execute", { session_id: state.sessionId, plan_id: planId });
      renderReceipt(receipt, { schema_valid: true, signature_valid: true });
      const stored = state.plans.get(planId);
      if (stored) renderPlan({ ...stored, status: receipt.status });
      setExecution(receipt.status, `Command ${String(receipt.status).replace("_", " ")}`, `${receipt.duration_ms} ms · signed receipt ready`);
      notify(`Execution ${String(receipt.status).replace("_", " ")}. The signed receipt is ready.`, receipt.status === "succeeded" ? "info" : "error");
    } catch (error) {
      setExecution("failed", "Execution refused", readableError(error));
      notify(readableError(error), "error");
    } finally {
      state.activePlanId = "";
      setControls();
      const stored = state.plans.get(planId);
      if (stored) renderPlan(stored);
    }
  }

  function lockPlanActions(planId, locked) {
    const card = ui.planLedger.querySelector(`[data-plan-id="${CSS.escape(planId)}"]`);
    if (!card) return;
    card.querySelectorAll(".plan-actions button").forEach((button) => {
      button.disabled = locked;
    });
  }

  async function retryPlan(planId) {
    try {
      const plan = await tool("terminal_retry", { session_id: state.sessionId, plan_id: planId });
      renderPlan(plan).scrollIntoView({ behavior: "smooth", block: "nearest" });
      notify("A fresh plan was created. Policy and approval were evaluated again.");
    } catch (error) {
      notify(readableError(error), "error");
    }
  }

  async function control(toolName, successLabel) {
    try {
      const result = await tool(toolName, { session_id: state.sessionId });
      const accepted = Object.values(result)[0];
      if (!accepted) throw new Error("No active command accepted this control action.");
      notify(successLabel);
    } catch (error) {
      notify(readableError(error), "error");
    }
  }

  function renderReceipt(receipt, validation) {
    state.currentReceipt = receipt;
    ui.receiptEmpty.hidden = true;
    ui.receiptPaper.hidden = false;
    ui.exportReceiptButton.disabled = false;
    ui.copyReceiptButton.disabled = false;
    const verified = Boolean(validation?.schema_valid && validation?.signature_valid);
    ui.receiptSeal.dataset.state = verified ? "valid" : "invalid";
    ui.receiptSeal.textContent = verified ? "VERIFIED" : validation?.schema_valid ? "BAD SIGNATURE" : "INVALID";
    ui.receiptStatus.textContent = receipt.status || "unknown";
    ui.receiptDuration.textContent = `${receipt.duration_ms ?? "—"} ms`;
    ui.receiptId.textContent = compactId(receipt.id);
    ui.receiptId.title = receipt.id || "";
    ui.receiptSession.textContent = compactId(receipt.session_id);
    ui.receiptSession.title = receipt.session_id || "";
    const permission = receipt.policy?.requires_approval
      ? receipt.approved
        ? "explicit approval"
        : "approval missing"
      : "policy allowed";
    ui.receiptPermission.textContent = `${receipt.mode || "—"} / ${permission}`;
    const exit = receipt.exit_code === null || receipt.exit_code === undefined ? "—" : receipt.exit_code;
    const executionSignal = receipt.signal === null || receipt.signal === undefined ? "—" : receipt.signal;
    ui.receiptExit.textContent = `${exit} / ${executionSignal}`;
    ui.receiptCommand.textContent = receipt.command || "";
    ui.receiptStdout.textContent = receipt.stdout || "(empty)";
    ui.receiptStderr.textContent = receipt.stderr || "(empty)";
    ui.receiptSignature.textContent = receipt.signature || "unsigned";
  }

  async function validateAndRenderReceipt(receipt) {
    const response = await fetch("/receipts/validate", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ receipt }),
    });
    const validation = await response.json();
    renderReceipt(receipt, validation);
    if (validation.signature_valid) {
      notify("Imported receipt schema and signature are valid.");
    } else {
      const detail = validation.errors?.[0] || "The signature does not match this server token.";
      notify(`Imported receipt is not trusted: ${detail}`, "error");
    }
  }

  async function importReceipt(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 2_000_000) {
      notify("Receipt import is limited to 2 MB.", "error");
      return;
    }
    try {
      const receipt = JSON.parse(await file.text());
      await validateAndRenderReceipt(receipt);
    } catch (error) {
      notify(`Receipt import failed: ${readableError(error)}`, "error");
    }
  }

  async function exportReceipt() {
    if (!state.currentReceipt) return;
    ui.exportReceiptButton.disabled = true;
    try {
      const response = await request("/receipts/redact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receipt: state.currentReceipt }),
      });
      const exportedReceipt = response.receipt;
      const blob = new Blob([`${JSON.stringify(exportedReceipt, null, 2)}\n`], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `term-mcp-receipt-${exportedReceipt.id || "export"}-redacted.json`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
      notify("A redacted, re-signed receipt was exported. Local output was not included.");
    } catch (error) {
      notify(`Receipt export failed: ${readableError(error)}`, "error");
    } finally {
      ui.exportReceiptButton.disabled = false;
    }
  }

  async function copyText(value, successMessage) {
    try {
      await navigator.clipboard.writeText(value);
      notify(successMessage);
    } catch (_error) {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
      notify(successMessage);
    }
  }

  async function askAdvisor(event) {
    event.preventDefault();
    const message = ui.advisorInput.value.trim();
    if (!message) return;
    ui.advisorButton.disabled = true;
    ui.advisorButton.textContent = "Waiting…";
    ui.advisorResponse.hidden = false;
    ui.advisorText.textContent = "Waiting for an advisory response. No command can execute here.";
    try {
      const response = await request("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId, message }),
      });
      ui.advisorText.textContent = response.message;
    } catch (error) {
      ui.advisorText.textContent = `Model unavailable: ${readableError(error)} Local terminal tools remain available.`;
      notify("DeepSeek is unavailable; local planning and execution are unaffected.", "error");
    } finally {
      ui.advisorButton.disabled = false;
      ui.advisorButton.textContent = "Ask advisor";
    }
  }

  async function loadScenarios() {
    try {
      const response = await fetch("/demo/scenarios");
      const payload = await response.json();
      ui.scenarioList.replaceChildren();
      payload.scenarios.forEach((scenario, index) => {
        const button = document.createElement("button");
        button.className = "scenario-button";
        button.type = "button";
        const number = document.createElement("span");
        number.className = "scenario-number";
        number.textContent = String(index + 1).padStart(2, "0");
        const copy = document.createElement("span");
        const label = document.createElement("strong");
        const outcome = document.createElement("small");
        label.textContent = scenario.label;
        outcome.textContent = scenario.outcome;
        copy.append(label, outcome);
        button.append(number, copy);
        button.addEventListener("click", () => {
          ui.commandInput.value = scenario.command;
          ui.commandInput.focus();
          notify(`Loaded “${scenario.label}”. Build its plan to continue.`);
        });
        ui.scenarioList.append(button);
      });
    } catch (_error) {
      const message = document.createElement("p");
      message.className = "rail-copy";
      message.textContent = "Guided scenarios are unavailable.";
      ui.scenarioList.replaceChildren(message);
    }
  }

  ui.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.token = ui.tokenInput.value.trim();
    sessionStorage.setItem(TOKEN_KEY, state.token);
    try {
      await connect();
    } catch (error) {
      sessionStorage.removeItem(TOKEN_KEY);
      state.token = "";
      setConnection("offline", "Locked");
      ui.authError.textContent = readableError(error);
      ui.tokenInput.focus();
      ui.tokenInput.select();
    }
  });

  ui.commandForm.addEventListener("submit", buildPlan);
  ui.newSessionButton.addEventListener("click", newSession);
  ui.lockButton.addEventListener("click", lock);
  ui.pauseButton.addEventListener("click", () => control("terminal_pause", "Pause requested."));
  ui.resumeButton.addEventListener("click", () => control("terminal_resume", "Resume requested."));
  ui.cancelButton.addEventListener("click", () => control("terminal_cancel", "Cancellation requested."));
  ui.noticeClose.addEventListener("click", clearNotice);
  ui.advisorForm.addEventListener("submit", askAdvisor);
  ui.importReceiptButton.addEventListener("click", () => ui.receiptFileInput.click());
  ui.receiptFileInput.addEventListener("change", importReceipt);
  ui.exportReceiptButton.addEventListener("click", () => void exportReceipt());
  ui.copyReceiptButton.addEventListener("click", () => {
    if (state.currentReceipt) {
      void copyText(JSON.stringify(state.currentReceipt, null, 2), "Receipt JSON copied.");
    }
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void buildPlan();
    } else if (event.key === "/" && !typing && ui.authGate.hidden) {
      event.preventDefault();
      ui.commandInput.focus();
    } else if (event.key === "Escape") {
      clearNotice();
    }
  });

  window.addEventListener("pagehide", () => state.streamController?.abort());
  void loadScenarios();
  if (state.token) {
    void connect().catch(async (error) => {
      await lock();
      ui.authError.textContent = readableError(error);
    });
  } else {
    setConnection("offline", "Locked");
    ui.tokenInput.focus();
  }
})();
