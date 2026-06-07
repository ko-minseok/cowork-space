List all available slash commands in this repository.

Print the following table exactly as shown, then stop.

---

## Wiki commands

| Command | Argument | Purpose |
|---------|----------|---------|
| `/wiki:ingest` | `<path or URL>` | Ingest a source file and update wiki pages |
| `/wiki:query` | `[--file-answer] <question>` | Answer a question from the wiki |
| `/wiki:lint` | *(none)* | Health-check the wiki and fix issues |
| `/wiki:new-page` | `<type> <title>` | Create a new wiki page stub from template |

## Dev commands

| Command | Argument | Purpose |
|---------|----------|---------|
| `/dev:commit` | `[subject line]` | Create a clean, scoped git commit |
| `/dev:review` | `[base..head]` | Review the current diff for real problems |
| `/dev:test` | `[filter]` | Run the test suite and diagnose failures |
| `/dev:standup` | `[since period]` | Generate a standup from recent git activity |
| `/dev:cleanup` | *(none)* | Find dead code, stale comments, orphaned files |

## Skill authoring

| Command | Argument | Purpose |
|---------|----------|---------|
| `/skill-creator` | `[skill name or description]` | Create, test, improve, and package a new skill |

Supporting scripts in `scripts/skill-creator/`:

| Script | Purpose |
|--------|---------|
| `quick_validate.py <dir>` | Validate SKILL.md frontmatter |
| `run_eval.py <evals.json> --skill-dir <dir>` | Test trigger rate |
| `run_loop.py <evals.json> <dir>` | Iterative description improvement |
| `generate_report.py <history.json> -o report.html` | HTML progress report |
| `aggregate_benchmark.py <benchmark-dir>` | Compare with/without skill |
| `package_skill.py <dir> [dist/]` | Package as `.skill` ZIP |

## Meta

| Command | Purpose |
|---------|---------|
| `/help` | Show this list |

---

For full instructions on any command, read `.claude/commands/<group>/<name>.md`.
