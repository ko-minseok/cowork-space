#!/bin/bash
# SessionStart hook: sync repo and validate wiki health.
# Runs only in remote (Claude Code on the web) environments.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}"
cd "$REPO_DIR"

echo "[session-start] Fetching latest changes from origin..."
git fetch origin

BRANCH=$(git rev-parse --abbrev-ref HEAD)
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "$LOCAL")

if [ "$LOCAL" != "$REMOTE" ]; then
  echo "[session-start] Pulling $BRANCH ($(git rev-list --count HEAD..origin/$BRANCH) new commit(s))..."
  git pull --ff-only origin "$BRANCH"
else
  echo "[session-start] Already up to date."
fi

# Ensure PyYAML is available (needed by scripts/skill-creator/quick_validate.py)
if ! python3 -c "import yaml" 2>/dev/null; then
  echo "[session-start] Installing PyYAML..."
  pip install --quiet pyyaml
fi

# Persist PYTHONPATH so scripts resolve sibling imports without pip install
echo 'export PYTHONPATH="${CLAUDE_PROJECT_DIR:-.}:${PYTHONPATH:-}"' >> "${CLAUDE_ENV_FILE:-/dev/null}"

# Ensure open-code-review CLI is available
if ! command -v ocr &>/dev/null; then
  echo "[session-start] Installing open-code-review..."
  npm install -g @alibaba-group/open-code-review --silent
else
  echo "[session-start] ocr $(ocr --version 2>/dev/null | head -1) already installed."
fi

echo "[session-start] Running wiki lint..."
python3 scripts/wiki/lint.py && echo "[session-start] Wiki healthy." || echo "[session-start] Wiki issues found — run /wiki:lint to fix."

echo "[session-start] Done."
