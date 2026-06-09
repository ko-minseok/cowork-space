#!/usr/bin/env bash
# Bootstrap a long-running Claude Agent workspace.
#
# Usage:
#   ./init.sh                          # start server against current dir
#   ./init.sh https://github.com/u/r  # clone repo, then start
#   ./init.sh https://github.com/u/r main  # clone specific branch
#
# Environment variables (optional, can also be set in .env):
#   ANTHROPIC_API_KEY   required for the agent to call Claude
#   AGENT_PORT          HTTP port (default 8000)
#   WORKSPACE_DIR       where to clone / work (default ./workspace)

set -euo pipefail

# ── colour helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${BLUE}[init]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $*"; }
die()   { echo -e "${RED}[err]${NC}  $*" >&2; exit 1; }

# ── load .env if present ────────────────────────────────────────────────────
if [[ -f .env ]]; then
  info "Loading .env"
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

REPO_URL="${1:-}"
BRANCH="${2:-main}"
WORKSPACE_DIR="${WORKSPACE_DIR:-./workspace}"
AGENT_PORT="${AGENT_PORT:-8000}"

# ── 1. Python env ────────────────────────────────────────────────────────────
info "Checking Python (need 3.10+)…"
PYTHON=$(command -v python3 || command -v python || die "python not found")
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Found Python $PY_VER at $PYTHON"
[[ $(echo "$PY_VER >= 3.10" | bc -l 2>/dev/null || "$PYTHON" -c "import sys; print(int(sys.version_info >= (3,10)))") == "1" ]] \
  || die "Python 3.10+ required, got $PY_VER"

# virtual-env (skip if already inside one)
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ ! -d .venv ]]; then
    info "Creating .venv…"
    "$PYTHON" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  ok "Activated .venv"
fi

# ── 2. Install dependencies ──────────────────────────────────────────────────
if [[ -f requirements.txt ]]; then
  info "Installing Python dependencies…"
  pip install -q -r requirements.txt
  ok "Dependencies installed"
else
  warn "requirements.txt not found — installing core packages"
  pip install -q claude-agent-sdk "fastapi>=0.111" "uvicorn[standard]>=0.29"
fi

# ── 3. API key check ─────────────────────────────────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  warn "ANTHROPIC_API_KEY is not set — the agent will refuse to run."
  warn "Export it before sending messages:  export ANTHROPIC_API_KEY=sk-ant-…"
else
  ok "ANTHROPIC_API_KEY is set"
fi

# ── 4. Workspace directory ───────────────────────────────────────────────────
mkdir -p "$WORKSPACE_DIR"

# ── 5. Git repo ───────────────────────────────────────────────────────────────
if [[ -n "$REPO_URL" ]]; then
  REPO_NAME=$(basename "$REPO_URL" .git)
  CLONE_DIR="$WORKSPACE_DIR/$REPO_NAME"
  if [[ -d "$CLONE_DIR/.git" ]]; then
    info "Repo already cloned at $CLONE_DIR — pulling latest…"
    git -C "$CLONE_DIR" fetch origin
    git -C "$CLONE_DIR" checkout "$BRANCH" 2>/dev/null || true
    git -C "$CLONE_DIR" pull --ff-only origin "$BRANCH" 2>/dev/null || true
  else
    info "Cloning $REPO_URL (branch: $BRANCH) → $CLONE_DIR"
    git clone --branch "$BRANCH" --depth 50 "$REPO_URL" "$CLONE_DIR"
  fi
  ok "Repo ready at $CLONE_DIR"
  export DEFAULT_CWD="$CLONE_DIR"
else
  export DEFAULT_CWD="$(pwd)"
fi

# ── 6. Scaffold workspace files if absent ────────────────────────────────────
PROGRESS_FILE="$WORKSPACE_DIR/claude-progress.txt"
FEATURES_FILE="$WORKSPACE_DIR/features.json"

if [[ ! -f "$PROGRESS_FILE" ]]; then
  cat > "$PROGRESS_FILE" <<EOF
# Claude Agent Progress Log
# Append-only — each session prepends a timestamped header.
# ──────────────────────────────────────────────────────────
# Initialised: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Workspace:   $WORKSPACE_DIR
EOF
  ok "Created $PROGRESS_FILE"
fi

if [[ ! -f "$FEATURES_FILE" ]]; then
  cat > "$FEATURES_FILE" <<'EOF'
[
  {
    "id": "f1",
    "title": "Example feature",
    "status": "todo",
    "priority": "medium",
    "notes": "Replace this with your real feature list."
  }
]
EOF
  ok "Created $FEATURES_FILE"
fi

# ── 7. Write runtime config ───────────────────────────────────────────────────
cat > "$WORKSPACE_DIR/.agent-config.json" <<EOF
{
  "workspace_dir": "$(realpath "$WORKSPACE_DIR")",
  "default_cwd": "$(realpath "${DEFAULT_CWD:-.}")",
  "progress_file": "$(realpath "$PROGRESS_FILE")",
  "features_file": "$(realpath "$FEATURES_FILE")",
  "port": $AGENT_PORT,
  "initialised_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
ok "Runtime config written to $WORKSPACE_DIR/.agent-config.json"

# ── 8. Start server ───────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Starting Claude Agent web server…${NC}"
echo -e "  URL:       ${GREEN}http://localhost:$AGENT_PORT${NC}"
echo -e "  Workspace: ${GREEN}$(realpath "$WORKSPACE_DIR")${NC}"
echo -e "  CWD:       ${GREEN}$(realpath "${DEFAULT_CWD:-.}")${NC}"
echo ""

AGENT_WORKSPACE_DIR="$(realpath "$WORKSPACE_DIR")" \
AGENT_DEFAULT_CWD="$(realpath "${DEFAULT_CWD:-.}")" \
  uvicorn src.agent_web.main:app \
    --host 0.0.0.0 \
    --port "$AGENT_PORT" \
    --reload \
    --reload-dir src/agent_web
