"""
Agent web server — FastAPI + Claude Agent SDK.

Exposes a streaming chat endpoint and a minimal web UI.
Run: uvicorn src.agent_web.main:app --reload
"""

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Claude Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        SystemMessage,
        ToolResultMessage,
        query,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

app = FastAPI(title="Claude Agent Web")
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

# ---------------------------------------------------------------------------
# Session store — in-memory, keyed by session_id.
# Each session holds a list of serialised message dicts for the UI.
# ---------------------------------------------------------------------------

@dataclass
class Session:
    session_id: str
    messages: list[dict] = field(default_factory=list)

_sessions: dict[str, Session] = {}


def _get_or_create(session_id: str) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id=session_id)
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    prompt: str
    session_id: str | None = None
    allowed_tools: list[str] = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
    max_turns: int = 20
    system_prompt: str | None = None
    cwd: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(event_type: str, data: dict) -> str:
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


async def _run_agent(req: ChatRequest, session: Session) -> AsyncIterator[str]:
    """Drive the agent and yield SSE-formatted strings."""

    if not SDK_AVAILABLE:
        yield _sse("error", {"text": "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"})
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        yield _sse("error", {"text": "ANTHROPIC_API_KEY environment variable not set."})
        return

    # Record the user turn
    user_msg = {"role": "user", "text": req.prompt}
    session.messages.append(user_msg)
    yield _sse("user", {"text": req.prompt, "session_id": session.session_id})

    opts_kwargs: dict = {
        "allowed_tools": req.allowed_tools,
        "permission_mode": "acceptEdits",
        "max_turns": req.max_turns,
    }
    if req.system_prompt:
        opts_kwargs["system_prompt"] = req.system_prompt
    if req.cwd:
        opts_kwargs["cwd"] = req.cwd

    opts = ClaudeAgentOptions(**opts_kwargs)

    try:
        async for message in query(prompt=req.prompt, options=opts):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        event = {"text": block.text}
                        session.messages.append({"role": "assistant", "text": block.text})
                        yield _sse("thinking", event)
                    elif hasattr(block, "name"):
                        # Tool use block
                        tool_input = getattr(block, "input", {})
                        event = {"name": block.name, "input": tool_input}
                        session.messages.append({"role": "tool_use", "name": block.name, "input": tool_input})
                        yield _sse("tool_use", event)

            elif isinstance(message, ToolResultMessage):
                content = getattr(message, "content", [])
                texts = [b.get("text", "") for b in content if isinstance(b, dict) and "text" in b]
                result_text = "\n".join(texts)
                event = {"text": result_text}
                session.messages.append({"role": "tool_result", "text": result_text})
                yield _sse("tool_result", event)

            elif isinstance(message, ResultMessage):
                result_text = getattr(message, "result", "")
                event = {"text": result_text, "session_id": session.session_id}
                session.messages.append({"role": "result", "text": result_text})
                yield _sse("result", event)

            elif isinstance(message, SystemMessage):
                subtype = getattr(message, "subtype", "")
                event = {"subtype": subtype}
                yield _sse("system", event)

    except Exception as exc:
        yield _sse("error", {"text": str(exc)})

    yield _sse("done", {})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    template = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template) as f:
        return f.read()


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    session = _get_or_create(session_id)

    return StreamingResponse(
        _run_agent(req, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(session_id=session_id, messages=session.messages)


@app.get("/sessions", response_model=list[str])
async def list_sessions():
    return list(_sessions.keys())


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"deleted": session_id}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "sdk_available": SDK_AVAILABLE,
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
