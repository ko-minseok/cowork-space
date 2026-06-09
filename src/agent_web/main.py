"""
Agent web server — FastAPI + Claude Agent SDK.

Long-running features:
  - Sessions persisted to disk (workspace/sessions/)
  - claude-progress.txt append-only log
  - features.json feature tracking
  - Git status / log / diff / clone / pull routes

Run:  ./init.sh
 or:  uvicorn src.agent_web.main:app --reload
"""

import json
import os
import uuid
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent_web import workspace as ws

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
# In-memory session cache backed by disk
# ---------------------------------------------------------------------------

class Session:
    def __init__(self, session_id: str, messages: list[dict] | None = None):
        self.session_id = session_id
        self.messages: list[dict] = messages or []

    def flush(self) -> None:
        ws.save_session(self.session_id, self.messages)


_cache: dict[str, Session] = {}


def _get_or_create(session_id: str) -> Session:
    if session_id not in _cache:
        saved = ws.load_session(session_id)
        _cache[session_id] = Session(session_id, saved)
    return _cache[session_id]


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
    log_progress: bool = True   # append result to claude-progress.txt


class SessionResponse(BaseModel):
    session_id: str
    messages: list[dict]


class FeatureIn(BaseModel):
    id: str | None = None
    title: str
    status: str = "todo"
    priority: str = "medium"
    notes: str = ""


class GitCloneRequest(BaseModel):
    url: str
    branch: str = "main"
    target_dir: str | None = None


class ProgressAppendRequest(BaseModel):
    text: str
    session_id: str | None = None


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


async def _run_agent(req: ChatRequest, session: Session) -> AsyncIterator[str]:
    if not SDK_AVAILABLE:
        yield _sse("error", {"text": "claude-agent-sdk not installed. Run: pip install claude-agent-sdk"})
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        yield _sse("error", {"text": "ANTHROPIC_API_KEY environment variable not set."})
        return

    session.messages.append({"role": "user", "text": req.prompt})
    session.flush()
    yield _sse("user", {"text": req.prompt, "session_id": session.session_id})

    effective_cwd = req.cwd or os.environ.get("AGENT_DEFAULT_CWD")

    opts_kwargs: dict = {
        "allowed_tools": req.allowed_tools,
        "permission_mode": "acceptEdits",
        "max_turns": req.max_turns,
    }
    if req.system_prompt:
        opts_kwargs["system_prompt"] = req.system_prompt
    if effective_cwd:
        opts_kwargs["cwd"] = effective_cwd

    opts = ClaudeAgentOptions(**opts_kwargs)
    final_result: str = ""

    try:
        async for message in query(prompt=req.prompt, options=opts):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        session.messages.append({"role": "assistant", "text": block.text})
                        yield _sse("thinking", {"text": block.text})
                    elif hasattr(block, "name"):
                        tool_input = getattr(block, "input", {})
                        session.messages.append({"role": "tool_use", "name": block.name, "input": tool_input})
                        yield _sse("tool_use", {"name": block.name, "input": tool_input})

            elif isinstance(message, ToolResultMessage):
                content = getattr(message, "content", [])
                texts = [b.get("text", "") for b in content if isinstance(b, dict)]
                result_text = "\n".join(t for t in texts if t)
                session.messages.append({"role": "tool_result", "text": result_text})
                yield _sse("tool_result", {"text": result_text})

            elif isinstance(message, ResultMessage):
                final_result = getattr(message, "result", "")
                session.messages.append({"role": "result", "text": final_result})
                yield _sse("result", {"text": final_result, "session_id": session.session_id})

            elif isinstance(message, SystemMessage):
                subtype = getattr(message, "subtype", "")
                yield _sse("system", {"subtype": subtype})

    except Exception as exc:
        yield _sse("error", {"text": str(exc)})
    finally:
        session.flush()

    # Persist to progress log
    if req.log_progress and final_result:
        ws.append_progress(
            f"Prompt: {req.prompt}\n\nResult:\n{final_result}",
            session_id=session.session_id,
        )

    yield _sse("done", {})


# ---------------------------------------------------------------------------
# Routes — UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    template = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template) as f:
        return f.read()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "sdk_available": SDK_AVAILABLE,
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "workspace_dir": os.environ.get("AGENT_WORKSPACE_DIR", "./workspace"),
        "default_cwd": os.environ.get("AGENT_DEFAULT_CWD", os.getcwd()),
    }


# ---------------------------------------------------------------------------
# Routes — Chat
# ---------------------------------------------------------------------------

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    session = _get_or_create(session_id)
    return StreamingResponse(
        _run_agent(req, session),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Routes — Sessions
# ---------------------------------------------------------------------------

@app.get("/sessions", response_model=list[str])
async def list_sessions():
    return ws.list_session_ids()


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    session = _get_or_create(session_id)
    if not session.messages and ws.load_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(session_id=session_id, messages=session.messages)


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    _cache.pop(session_id, None)
    ws.delete_session_file(session_id)
    return {"deleted": session_id}


# ---------------------------------------------------------------------------
# Routes — Progress log
# ---------------------------------------------------------------------------

@app.get("/progress")
async def get_progress():
    return {"content": ws.read_progress()}


@app.post("/progress")
async def append_progress(req: ProgressAppendRequest):
    ws.append_progress(req.text, req.session_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Routes — Feature list
# ---------------------------------------------------------------------------

@app.get("/features")
async def list_features():
    return [asdict(f) for f in ws.load_features()]


@app.post("/features")
async def create_feature(req: FeatureIn):
    feature_id = req.id or str(uuid.uuid4())[:8]
    feature = ws.Feature(
        id=feature_id,
        title=req.title,
        status=req.status,
        priority=req.priority,
        notes=req.notes,
    )
    features = ws.upsert_feature(feature)
    return [asdict(f) for f in features]


@app.patch("/features/{feature_id}")
async def update_feature(feature_id: str, req: FeatureIn):
    features = ws.load_features()
    existing = next((f for f in features if f.id == feature_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Feature not found")
    existing.title = req.title
    existing.status = req.status
    existing.priority = req.priority
    existing.notes = req.notes
    updated = ws.upsert_feature(existing)
    return [asdict(f) for f in updated]


@app.delete("/features/{feature_id}")
async def delete_feature(feature_id: str):
    features = ws.delete_feature(feature_id)
    return [asdict(f) for f in features]


# ---------------------------------------------------------------------------
# Routes — Git
# ---------------------------------------------------------------------------

@app.get("/git/status")
async def git_status(cwd: str | None = None):
    effective = cwd or os.environ.get("AGENT_DEFAULT_CWD")
    if not effective or not ws.git_is_repo(effective):
        return {"is_repo": False}
    status = ws.git_status(effective)
    return {"is_repo": True, **status}


@app.get("/git/log")
async def git_log(n: int = 10, cwd: str | None = None):
    effective = cwd or os.environ.get("AGENT_DEFAULT_CWD")
    if not effective or not ws.git_is_repo(effective):
        return []
    return ws.git_log(n, effective)


@app.get("/git/diff")
async def git_diff(staged: bool = False, cwd: str | None = None):
    effective = cwd or os.environ.get("AGENT_DEFAULT_CWD")
    if not effective or not ws.git_is_repo(effective):
        return {"diff": ""}
    return {"diff": ws.git_diff(staged, effective)}


@app.post("/git/clone")
async def git_clone(req: GitCloneRequest):
    ok, result = ws.git_clone(req.url, req.branch, req.target_dir)
    if not ok:
        raise HTTPException(status_code=400, detail=result)
    return {"cloned_to": result}


@app.post("/git/pull")
async def git_pull(cwd: str | None = None):
    effective = cwd or os.environ.get("AGENT_DEFAULT_CWD")
    if not effective or not ws.git_is_repo(effective):
        raise HTTPException(status_code=400, detail="Not a git repository")
    ok, msg = ws.git_pull(effective)
    return {"ok": ok, "message": msg}
