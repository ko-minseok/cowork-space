---
name: skill-creator
description: >
  Use this skill when the user wants to create a new Claude Code skill (slash command),
  improve an existing skill's description or instructions, validate a skill file,
  run evals to test whether a skill triggers correctly, or package a skill for distribution.
  Triggers on: "create a skill", "add a slash command", "improve skill description",
  "validate skill", "run skill evals", "package skill", "test if skill triggers".
---

# Skill Creator: Core Workflow

You are helping the user build, test, and iterate on Claude Code skills.
A skill is a `.md` file in `.claude/commands/` with a YAML frontmatter block (`---`) containing
`name` and `description`, followed by instructions for Claude.

## Workflow stages

### 1. Capture intent
Ask (or infer from $ARGUMENTS):
- What should the skill do?
- When should it trigger? (give 3–5 example user phrases)
- What does a good output look like?
- Do test cases exist, or should you draft them?

### 2. Draft the skill
Create `SKILL.md` at the correct path using the schema in `references/schemas.md`.
- `name`: kebab-case, ≤ 64 chars
- `description`: ≤ 1024 chars, no angle brackets, written so Claude recognises when to trigger it
- Body: imperative instructions, explain *why* not just *what*, ≤ 500 lines

Run quick validation immediately:
```bash
python scripts/skill-creator/quick_validate.py .claude/commands/<skill-name>
```

### 3. Test & evaluate
Draft an `evals.json` alongside the skill (see schema in `references/schemas.md`).
Run evals:
```bash
python scripts/skill-creator/run_eval.py .claude/commands/<skill-name>/evals.json \
  --skill-dir .claude/commands/<skill-name>
```
Generate a review report while evals run:
```bash
python scripts/skill-creator/generate_report.py - -o /tmp/skill-report.html \
  --skill-name <skill-name>
```

### 4. Improve
Analyse failures with the analyzer agent (`agents/analyzer.md`).
If description trigger rate is low, run the improvement loop:
```bash
python scripts/skill-creator/run_loop.py \
  .claude/commands/<skill-name>/evals.json \
  .claude/commands/<skill-name> \
  --max-iterations 5
```

### 5. Package (optional)
When the skill is ready to share:
```bash
python scripts/skill-creator/package_skill.py .claude/commands/<skill-name> ./dist
```

## Key principles
- **Progressive disclosure**: frontmatter always loads; body loads on trigger only.
- **Theory of mind**: write instructions so Claude understands *why*, not just *what*.
- **Avoid MUST/NEVER** unless truly non-negotiable — prefer explaining the consequence.
- **Generalise from examples** — don't overfit instructions to one test case.
- **Human review first** — generate the report *before* reading results yourself.
