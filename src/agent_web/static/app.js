"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentSessionId = null;
let isStreaming = false;

const ALL_TOOLS = [
  "Read", "Write", "Edit", "Bash", "Glob", "Grep",
  "WebSearch", "WebFetch", "AskUserQuestion",
];
let activeTools = new Set(["Read", "Write", "Edit", "Bash", "Glob", "Grep"]);

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt-input");
const sendBtn = document.getElementById("send-btn");
const cwdInput = document.getElementById("cwd");
const systemPromptInput = document.getElementById("system-prompt");
const maxTurnsInput = document.getElementById("max-turns");
const toolGrid = document.getElementById("tool-grid");
const sessionList = document.getElementById("session-list");
const newSessionBtn = document.getElementById("new-session-btn");

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
      if (activeTools.has(tool)) activeTools.delete(tool);
      else activeTools.add(tool);
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
      li.textContent = id.slice(0, 8) + "…";
      li.title = id;
      if (id === currentSessionId) li.classList.add("active");
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
      appendMessage(msg.role, formatStoredMessage(msg), false);
    }
    scrollToBottom();
    loadSessionList();
  } catch (e) {
    appendMessage("error", "Failed to load session: " + e.message);
  }
}

function formatStoredMessage(msg) {
  if (msg.role === "tool_use") return formatToolUse(msg.name, msg.input);
  return msg.text || "";
}

// ---------------------------------------------------------------------------
// Message rendering
// ---------------------------------------------------------------------------
const LABELS = {
  user: "You",
  thinking: "Claude",
  tool_use: "Tool call",
  tool_result: "Tool result",
  result: "Result",
  error: "Error",
  system: "System",
};

function formatToolUse(name, input) {
  const inputStr = input && Object.keys(input).length
    ? JSON.stringify(input, null, 2)
    : "";
  return `<div class="tool-header"><span class="tool-name">${esc(name)}</span></div>${inputStr ? `<div class="tool-input">${esc(inputStr)}</div>` : ""}`;
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function appendMessage(type, content, scroll = true) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${type}`;

  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = LABELS[type] ?? type;

  const body = document.createElement("div");
  body.className = "msg-body";

  // Allow pre-formatted HTML only for tool_use
  if (type === "tool_use") {
    body.innerHTML = content;
  } else {
    body.textContent = content;
  }

  wrapper.appendChild(label);
  wrapper.appendChild(body);
  messagesEl.appendChild(wrapper);

  if (scroll) scrollToBottom();
  return body; // return so we can update streaming text
}

function showTyping() {
  const el = document.createElement("div");
  el.id = "typing";
  el.className = "typing-indicator";
  el.innerHTML = "<span></span><span></span><span></span>";
  messagesEl.appendChild(el);
  scrollToBottom();
}

function hideTyping() {
  document.getElementById("typing")?.remove();
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ---------------------------------------------------------------------------
// Streaming chat
// ---------------------------------------------------------------------------
async function sendMessage(prompt) {
  if (!prompt.trim() || isStreaming) return;
  isStreaming = true;
  sendBtn.disabled = true;

  const payload = {
    prompt: prompt.trim(),
    session_id: currentSessionId,
    allowed_tools: [...activeTools],
    max_turns: parseInt(maxTurnsInput.value) || 20,
    system_prompt: systemPromptInput.value.trim() || null,
    cwd: cwdInput.value.trim() || null,
  };

  showTyping();

  let thinkingBody = null; // accumulate streaming thinking text

  try {
    const res = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      hideTyping();
      appendMessage("error", `Server error: ${res.status}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete line

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
            // Merge consecutive thinking chunks into one bubble
            if (!thinkingBody) {
              thinkingBody = appendMessage("thinking", event.text);
            } else {
              thinkingBody.textContent += "\n\n" + event.text;
              scrollToBottom();
            }
            break;

          case "tool_use":
            thinkingBody = null; // reset for next thinking segment
            appendMessage("tool_use", formatToolUse(event.name, event.input));
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
            if (event.subtype) {
              appendMessage("system", `[${event.subtype}]`);
            }
            break;

          case "done":
            hideTyping();
            loadSessionList();
            break;
        }
      }
    }
  } catch (err) {
    hideTyping();
    appendMessage("error", err.message);
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    thinkingBody = null;
    promptInput.focus();
  }
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const prompt = promptInput.value;
  promptInput.value = "";
  sendMessage(prompt);
});

// Cmd/Ctrl+Enter to submit
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
