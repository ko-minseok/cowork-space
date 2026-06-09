"""
Workspace manager for long-running agent sessions.

Handles:
  - Disk-persisted sessions  (sessions/ dir as JSON)
  - claude-progress.txt      (append-only agent progress log)
  - features.json            (feature list with status tracking)
  - Git operations           (clone, status, log, diff, commit)
"""

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Workspace root — resolved from env or defaults to ./workspace
# ---------------------------------------------------------------------------

def _workspace_root() -> Path:
    raw = os.environ.get("AGENT_WORKSPACE_DIR", "./workspace")
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def sessions_dir() -> Path:
    d = _workspace_root() / "sessions"
    d.mkdir(exist_ok=True)
    return d


def save_session(session_id: str, messages: list[dict]) -> None:
    path = sessions_dir() / f"{session_id}.json"
    path.write_text(json.dumps({"session_id": session_id, "messages": messages}, indent=2))


def load_session(session_id: str) -> list[dict] | None:
    path = sessions_dir() / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data.get("messages", [])


def list_session_ids() -> list[str]:
    return sorted(
        (p.stem for p in sessions_dir().glob("*.json")),
        key=lambda s: (sessions_dir() / f"{s}.json").stat().st_mtime,
        reverse=True,
    )


def delete_session_file(session_id: str) -> None:
    path = sessions_dir() / f"{session_id}.json"
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# claude-progress.txt
# ---------------------------------------------------------------------------

def _progress_path() -> Path:
    raw = os.environ.get("AGENT_WORKSPACE_DIR", "./workspace")
    root = Path(raw).expanduser().resolve()
    return root / "claude-progress.txt"


def read_progress() -> str:
    p = _progress_path()
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def append_progress(text: str, session_id: str | None = None) -> None:
    """Append a timestamped block to claude-progress.txt."""
    p = _progress_path()
    header = f"\n── {_utc_now()}"
    if session_id:
        header += f"  [{session_id[:8]}]"
    header += " ──\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(header + text.rstrip() + "\n")


# ---------------------------------------------------------------------------
# Feature list  (features.json)
# ---------------------------------------------------------------------------

VALID_STATUSES = {"todo", "in_progress", "done", "blocked"}
VALID_PRIORITIES = {"high", "medium", "low"}


@dataclass
class Feature:
    id: str
    title: str
    status: str = "todo"       # todo | in_progress | done | blocked
    priority: str = "medium"   # high | medium | low
    notes: str = ""
    updated_at: str = field(default_factory=_utc_now)


def _features_path() -> Path:
    raw = os.environ.get("AGENT_WORKSPACE_DIR", "./workspace")
    root = Path(raw).expanduser().resolve()
    return root / "features.json"


def load_features() -> list[Feature]:
    p = _features_path()
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [Feature(**{k: v for k, v in item.items() if k in Feature.__dataclass_fields__}) for item in raw]


def save_features(features: list[Feature]) -> None:
    _features_path().write_text(
        json.dumps([asdict(f) for f in features], indent=2, ensure_ascii=False)
    )


def upsert_feature(feature: Feature) -> list[Feature]:
    features = load_features()
    for i, f in enumerate(features):
        if f.id == feature.id:
            feature.updated_at = _utc_now()
            features[i] = feature
            save_features(features)
            return features
    feature.updated_at = _utc_now()
    features.append(feature)
    save_features(features)
    return features


def delete_feature(feature_id: str) -> list[Feature]:
    features = [f for f in load_features() if f.id != feature_id]
    save_features(features)
    return features


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _default_cwd() -> str:
    return os.environ.get("AGENT_DEFAULT_CWD", os.getcwd())


def _git(args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a git command; return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or _default_cwd(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_is_repo(cwd: str | None = None) -> bool:
    code, _, _ = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    return code == 0


def git_status(cwd: str | None = None) -> dict:
    _, out, _ = _git(["status", "--short", "--branch"], cwd)
    lines = out.splitlines()
    branch_line = lines[0] if lines else ""
    changes = [l for l in lines[1:] if l.strip()]
    return {"branch": branch_line.lstrip("## "), "changes": changes, "raw": out}


def git_log(n: int = 10, cwd: str | None = None) -> list[dict]:
    _, out, _ = _git(
        ["log", f"-{n}", "--pretty=format:%H|%s|%an|%ar"],
        cwd,
    )
    if not out:
        return []
    entries = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            entries.append({"hash": parts[0][:8], "subject": parts[1], "author": parts[2], "when": parts[3]})
    return entries


def git_diff(staged: bool = False, cwd: str | None = None) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    _, out, _ = _git(args, cwd)
    return out


def git_clone(url: str, branch: str = "main", target_dir: str | None = None) -> tuple[bool, str]:
    dest = target_dir or (_workspace_root() / Path(url).stem.replace(".git", "")).as_posix()
    if Path(dest).exists():
        return False, f"Directory already exists: {dest}"
    result = subprocess.run(
        ["git", "clone", "--branch", branch, "--depth", "50", url, dest],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, dest


def git_pull(cwd: str | None = None) -> tuple[bool, str]:
    code, out, err = _git(["pull", "--ff-only"], cwd)
    return code == 0, out or err
