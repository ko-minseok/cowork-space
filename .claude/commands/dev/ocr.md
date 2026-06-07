Run an AI-powered deep code review using open-code-review (ocr).
Use this for thorough, line-level review of diffs. For a quick philosophy-based review, use /dev:review instead.

## Prerequisites check

First, verify ocr is installed and reachable:
```bash
ocr --version 2>/dev/null || echo "NOT_INSTALLED"
```

If not installed:
```bash
npm install -g @alibaba-group/open-code-review
```

Then verify LLM connectivity:
```bash
ocr llm test
```

If LLM is not configured, instruct the user to run:
```bash
ocr config set llm.url https://api.anthropic.com/v1/messages
ocr config set llm.auth_token <ANTHROPIC_API_KEY>
ocr config set llm.model claude-sonnet-4-6
ocr config set llm.use_anthropic true
```
Then stop and ask them to re-run the skill.

## Gather context

Before running the review, determine:
1. What is the target? (parse $ARGUMENTS or ask)
   - No argument → workspace (staged + unstaged + untracked)
   - `--commit <hash>` → single commit
   - `--from <base> --to <head>` → branch range
   - `--pr` or PR number → compare against main/master

2. Extract a one-sentence business context from:
   - The branch name (`git rev-parse --abbrev-ref HEAD`)
   - Recent commit messages (`git log --oneline -3`)
   - Any $ARGUMENTS description the user provided

## Run the review

Workspace mode (default):
```bash
ocr review --audience agent --background "<context>"
```

Branch/PR mode:
```bash
ocr review --audience agent \
  --from origin/main --to HEAD \
  --background "<context>"
```

Single commit:
```bash
ocr review --audience agent \
  --commit <hash> \
  --background "<context>"
```

Preview (which files would be reviewed, no LLM call):
```bash
ocr review --preview
```

## Classify and report findings

Parse the output and group findings by priority:

**High** — bugs, security issues, clear mistakes with a precise fix available.
Present these first with file:line reference and suggested fix.

**Medium** — context-dependent concerns, performance, style with real impact.
Present after High findings.

**Low** — silently discard. Do not report nitpicks or false positives.

Format each finding as:
```
[HIGH] src/foo.py:42 — Null dereference: `user` may be None before .name access
  Fix: add `if user is None: return` before line 42
```

## Apply fixes

Only apply fixes if the user explicitly asks ("fix it", "apply", "yes").
Never auto-apply. Always show the diff and ask for confirmation first.

## Usage examples

```
/dev:ocr                          # review workspace changes
/dev:ocr --from main --to HEAD    # review branch vs main
/dev:ocr --commit abc123          # review single commit
/dev:ocr --preview                # preview files without LLM
```
