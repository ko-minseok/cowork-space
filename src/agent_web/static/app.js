"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentSessionId = null;
let isStreaming = false;
let editingFeatureId = null;

const ALL_TOOLS = [
  "Read", "Write", "Edit", "Bash", "Glob", "Grep",
  "WebSearch", "WebFetch", "AskUserQuestion",
];
let activeTools = new Set(["Read", "Write", "Edit", "Bash", "Glob", "Grep"]);

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const messagesEl       = document.getElementById("messages");
const chatForm         = document.getElementById("chat-form");
const promptInput      = document.getElementById("prompt-input");
const sendBtn          = document.getElementById("send-btn");
const cwdInput         = document.getElementById("cwd");
const systemPromptInput = document.getElementById("system-prompt");
const maxTurnsInput    = document.getElementById("max-turns");
const logProgressChk   = document.getElementById("log-progress");
const toolGrid         = document.getElementById("tool-grid");
const sessionList      = document.getElementById("session-list");
const newSessionBtn    = document.getElementById("new-session-btn");
const apiStatusDot     = document.getElementById("api-status");

// Feature tab
const addFeatureBtn    = document.getElementById("add-feature-btn");
const featureForm      = document.getElementById("feature-form");
const ftTitle          = document.getElementById("ft-title");
const ftStatus         = document.getElementById("ft-status");
const ftPriority       = document.getElementById("ft-priority");
const ftNotes          = document.getElementById("ft-notes");
const ftSaveBtn        = document.getElementById("ft-save-btn");
const ftCancelBtn      = document.getElementById("ft-cancel-btn");
const featureListEl    = document.getElementById("feature-list");

// Git tab
const gitStatusBox     = document.getElementById("git-status-box");
const gitLogList       = document.getElementById("git-log-list");
const gitRefreshBtn    = document.getElementById("git-refresh-btn");
const cloneUrlInput    = document.getElementById("clone-url");
const cloneBranchInput = document.getElementById("clone-branch");
const cloneBtn         = document.getElementById("clone-btn");
const gitDiffBox       = document.getElementById("git-diff-box");

// Progress tab
const progressContent  = document.getElementById("progress-content");
const progressRefresh  = document.getElementById("progress-refresh-btn");

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    // Lazy load on tab switch
    if (btn.dataset.tab === "git") loadGit();
    if (btn.dataset.tab === "progress") loadProgress();
    if (btn.dataset.tab === "features") loadFeatures();
  });
});

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
async function checkHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    if (data.api_key_set) {
      apiStatusDot.className = "status-dot ok";
      apiStatusDot.title = "API key set ✓";
    } else {
      apiStatusDot.className = "status-dot error";
      apiStatusDot.title = "ANTHROPIC_API_KEY not set";
    }
    if (data.default_cwd && !cwdInput.value) {
      cwdInput.placeholder = data.default_cwd;
    }
  } catch {
    apiStatusDot.className = "status-dot error";
    apiStatusDot.title = "Server unreachable";
  }
}

// ---------------------------------------------------------------------------
// Tool chips
// ---------------------------------------------------------------------------
function renderToolChips() {
  toolGrid.innerHTML = "";
  for (const tool of ALL_TOOLS) {
    const chip = document.createElement("div");
    chip.className = "tool-chip" + (activeTools.has(tool) ? " active" : "");
    chip.textContent = tool;
    chip.addEventListener("click", () => {
      activeTools.has(tool) ? activeTools.delete(tool) : activeTools.add(tool);
      chip.classList.toggle("active");
    });
    toolGrid.appendChild(chip);
  }
}

// ---------------------------------------------------------------------------
// Session list
// ---------------------------------------------------------------------------
async function loadSessionList() {
  try {
    const res = await fetch("/sessions");
    const ids = await res.json();
    sessionList.innerHTML = "";
    for (const id of ids) {
      const li = document.createElement("li");
      if (id === currentSessionId) li.classList.add("active");
      const span = document.createElement("span");
      span.textContent = id.slice(0, 8) + "…";
      span.title = id;
      const del = document.createElement("span");
      del.className = "del-btn";
      del.textContent = "✕";
      del.title = "Delete session";
      del.addEventListener("click", async (e) => {
        e.stopPropagation();
        await fetch(`/sessions/${id}`, { method: "DELETE" });
        if (id === currentSessionId) { currentSessionId = null; messagesEl.innerHTML = ""; }
        loadSessionList();
      });
      li.appendChild(span);
      li.appendChild(del);
      li.addEventListener("click", () => loadSession(id));
      sessionList.appendChild(li);
    }
  } catch (_) {}
}

async function loadSession(sessionId) {
  currentSessionId = sessionId;
  try {
    const res = await fetch(`/sessions/${sessionId}`);
    const data = await res.json();
    messagesEl.innerHTML = "";
    for (const msg of data.messages) {
      const content = msg.role === "tool_use" ? formatToolUse(msg.name, msg.input) : (msg.text || "");
      appendMessage(msg.role, content, false, msg.role === "tool_use");
    }
    scrollToBottom();
    loadSessionList();
  } catch (e) {
    appendMessage("error", "Failed to load session: " + e.message);
  }
}

// ---------------------------------------------------------------------------
// Features
// ---------------------------------------------------------------------------
async function loadFeatures() {
  try {
    const res = await fetch("/features");
    const features = await res.json();
    renderFeatures(features);
  } catch { featureListEl.innerHTML = "<li style='color:var(--muted);padding:8px 14px;font-size:11px'>Failed to load</li>"; }
}

function renderFeatures(features) {
  featureListEl.innerHTML = "";
  if (!features.length) {
    featureListEl.innerHTML = "<li style='color:var(--muted);font-size:11px;padding:4px 0'>No features yet</li>";
    return;
  }
  for (const f of features) {
    const li = document.createElement("li");
    li.className = `feature-item${f.status === "done" ? " done" : ""}`;
    li.dataset.id = f.id;
    li.innerHTML = `
      <div class="feature-header">
        <span class="feature-title">${esc(f.title)}</span>
        <span class="badge badge-${f.status}">${f.status.replace("_", " ")}</span>
        <span class="badge badge-${f.priority}">${f.priority}</span>
      </div>
      ${f.notes ? `<div class="feature-notes">${esc(f.notes)}</div>` : ""}
      <div class="feature-actions">
        ${["todo","in_progress","done","blocked"].filter(s => s !== f.status).map(s =>
          `<button class="btn-sm" data-action="status" data-val="${s}" data-id="${f.id}">${s.replace("_"," ")}</button>`
        ).join("")}
        <button class="btn-sm" data-action="edit" data-id="${f.id}">Edit</button>
        <button class="btn-sm btn-danger" data-action="delete" data-id="${f.id}">Del</button>
      </div>`;
    featureListEl.appendChild(li);
  }
}

featureListEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const id = btn.dataset.id;
  const action = btn.dataset.action;

  if (action === "delete") {
    const res = await fetch(`/features/${id}`, { method: "DELETE" });
    renderFeatures(await res.json());
  } else if (action === "status") {
    const features = await (await fetch("/features")).json();
    const f = features.find(x => x.id === id);
    if (!f) return;
    f.status = btn.dataset.val;
    const res = await fetch(`/features/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(f),
    });
    renderFeatures(await res.json());
  } else if (action === "edit") {
    const features = await (await fetch("/features")).json();
    const f = features.find(x => x.id === id);
    if (!f) return;
    editingFeatureId = id;
    ftTitle.value = f.title;
    ftStatus.value = f.status;
    ftPriority.value = f.priority;
    ftNotes.value = f.notes;
    featureForm.classList.remove("hidden");
  }
});

addFeatureBtn.addEventListener("click", () => {
  editingFeatureId = null;
  ftTitle.value = ""; ftStatus.value = "todo"; ftPriority.value = "medium"; ftNotes.value = "";
  featureForm.classList.remove("hidden");
  ftTitle.focus();
});

ftCancelBtn.addEventListener("click", () => { featureForm.classList.add("hidden"); editingFeatureId = null; });

ftSaveBtn.addEventListener("click", async () => {
  if (!ftTitle.value.trim()) return;
  const body = { title: ftTitle.value.trim(), status: ftStatus.value, priority: ftPriority.value, notes: ftNotes.value.trim() };
  let res;
  if (editingFeatureId) {
    res = await fetch(`/features/${editingFeatureId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } else {
    res = await fetch("/features", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  renderFeatures(await res.json());
  featureForm.classList.add("hidden");
  editingFeatureId = null;
});

// ---------------------------------------------------------------------------
// Git
// ---------------------------------------------------------------------------
async function loadGit() {
  try {
    const [statusRes, logRes, diffRes] = await Promise.all([
      fetch("/git/status"),
      fetch("/git/log?n=8"),
      fetch("/git/diff"),
    ]);
    const status = await statusRes.json();
    const log    = await logRes.json();
    const diff   = await diffRes.json();

    if (!status.is_repo) {
      gitStatusBox.textContent = "Not a git repository";
      gitLogList.innerHTML = "";
      gitDiffBox.textContent = "—";
      return;
    }

    gitStatusBox.textContent = status.raw || "Clean";

    gitLogList.innerHTML = "";
    for (const c of log) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="commit-hash">${esc(c.hash)}</span> <span class="commit-subject">${esc(c.subject)}</span><div class="commit-meta">${esc(c.author)} · ${esc(c.when)}</div>`;
      gitLogList.appendChild(li);
    }

    gitDiffBox.textContent = diff.diff || "No unstaged changes";
  } catch (e) {
    gitStatusBox.textContent = "Error: " + e.message;
  }
}

gitRefreshBtn.addEventListener("click", loadGit);

cloneBtn.addEventListener("click", async () => {
  const url = cloneUrlInput.value.trim();
  if (!url) return;
  cloneBtn.disabled = true; cloneBtn.textContent = "Cloning…";
  try {
    const res = await fetch("/git/clone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, branch: cloneBranchInput.value.trim() || "main" }),
    });
    const data = await res.json();
    if (res.ok) {
      cloneUrlInput.value = "";
      cwdInput.value = data.cloned_to;
      loadGit();
    } else {
      alert("Clone failed: " + data.detail);
    }
  } finally {
    cloneBtn.disabled = false; cloneBtn.textContent = "Clone";
  }
});

// ---------------------------------------------------------------------------
// Progress
// ---------------------------------------------------------------------------
async function loadProgress() {
  try {
    const res = await fetch("/progress");
    const data = await res.json();
    progressContent.textContent = data.content || "(empty)";
    progressContent.scrollTop = progressContent.scrollHeight;
  } catch { progressContent.textContent = "Failed to load"; }
}

progressRefresh.addEventListener("click", loadProgress);

// ---------------------------------------------------------------------------
// Message rendering
// ---------------------------------------------------------------------------
const LABELS = {
  user: "You", thinking: "Claude", tool_use: "Tool call",
  tool_result: "Tool result", result: "Result", error: "Error", system: "System",
};

function formatToolUse(name, input) {
  const inputStr = input && Object.keys(input).length ? JSON.stringify(input, null, 2) : "";
  return `<div class="tool-header"><span class="tool-name">${esc(name)}</span></div>${inputStr ? `<div class="tool-input">${esc(inputStr)}</div>` : ""}`;
}

function esc(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function appendMessage(type, content, scroll = true, isHtml = false) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${type}`;
  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = LABELS[type] ?? type;
  const body = document.createElement("div");
  body.className = "msg-body";
  if (isHtml) body.innerHTML = content;
  else body.textContent = content;
  wrapper.appendChild(label);
  wrapper.appendChild(body);
  messagesEl.appendChild(wrapper);
  if (scroll) scrollToBottom();
  return body;
}

function showTyping() {
  if (document.getElementById("typing")) return;
  const el = document.createElement("div");
  el.id = "typing"; el.className = "typing-indicator";
  el.innerHTML = "<span></span><span></span><span></span>";
  messagesEl.appendChild(el);
  scrollToBottom();
}

function hideTyping() { document.getElementById("typing")?.remove(); }
function scrollToBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

// ---------------------------------------------------------------------------
// Streaming chat
// ---------------------------------------------------------------------------
async function sendMessage(prompt) {
  if (!prompt.trim() || isStreaming) return;
  isStreaming = true; sendBtn.disabled = true;

  const payload = {
    prompt: prompt.trim(),
    session_id: currentSessionId,
    allowed_tools: [...activeTools],
    max_turns: parseInt(maxTurnsInput.value) || 20,
    system_prompt: systemPromptInput.value.trim() || null,
    cwd: cwdInput.value.trim() || null,
    log_progress: logProgressChk.checked,
  };

  showTyping();
  let thinkingBody = null;

  try {
    const res = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) { hideTyping(); appendMessage("error", `Server error: ${res.status}`); return; }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let event;
        try { event = JSON.parse(line.slice(6)); } catch { continue; }

        hideTyping();

        switch (event.type) {
          case "user":
            currentSessionId = event.session_id || currentSessionId;
            appendMessage("user", event.text);
            loadSessionList();
            break;

          case "thinking":
            if (!thinkingBody) thinkingBody = appendMessage("thinking", event.text);
            else { thinkingBody.textContent += "\n\n" + event.text; scrollToBottom(); }
            break;

          case "tool_use":
            thinkingBody = null;
            appendMessage("tool_use", formatToolUse(event.name, event.input), true, true);
            showTyping();
            break;

          case "tool_result":
            hideTyping();
            appendMessage("tool_result", event.text);
            showTyping();
            break;

          case "result":
            thinkingBody = null;
            appendMessage("result", event.text);
            break;

          case "error":
            appendMessage("error", event.text);
            break;

          case "system":
            if (event.subtype) appendMessage("system", `[${event.subtype}]`);
            break;

          case "done":
            hideTyping();
            loadSessionList();
            // Refresh progress if the tab is active
            if (document.querySelector(".tab[data-tab='progress']")?.classList.contains("active")) {
              loadProgress();
            }
            break;
        }
      }
    }
  } catch (err) {
    hideTyping(); appendMessage("error", err.message);
  } finally {
    isStreaming = false; sendBtn.disabled = false;
    thinkingBody = null; promptInput.focus();
  }
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = promptInput.value;
  promptInput.value = "";
  sendMessage(prompt);
});

promptInput.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    e.preventDefault();
    chatForm.dispatchEvent(new Event("submit"));
  }
});

newSessionBtn.addEventListener("click", () => {
  currentSessionId = null;
  messagesEl.innerHTML = "";
  loadSessionList();
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
renderToolChips();
loadSessionList();
checkHealth();
loadFeatures();
