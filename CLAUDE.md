# CLAUDE.md

This file guides AI agents (Claude Code and others) working in this repository.
Philosophy is inspired by [Andrej Karpathy's approach to readable, minimal, educational code](https://github.com/karpathy).

---

## Project Overview

> Fill in: what this project does, who it's for, and what problem it solves.

---

## Development Philosophy

Adapted from Karpathy's principles across nanoGPT, llm.c, micrograd, and public writing:

### 1. Clarity over cleverness
Write code a smart newcomer can read top-to-bottom without jumping around. If a reader needs to hold 5 things in their head at once, rewrite it.

### 2. Keep it small
Prefer one 300-line file to three 100-line files wired together with abstractions. Indirection has a cost. Pay it only when the benefit is obvious.

### 3. No premature abstraction
Don't generalize until you have three concrete cases that share the pattern. Abstract too early and you abstract the wrong thing.

### 4. Read the source
Don't hide behind library documentation. When something breaks, read the library source. Prefer dependencies you can fully read.

### 5. Iterate fast, understand deeply
Run something. Look at the output. Form a hypothesis. Change one thing. Repeat. Don't redesign before you've shipped.

### 6. Defaults are wrong
Question every default (learning rate, batch size, framework choice). Know what each knob does before you touch it.

### 7. Reproducibility is non-negotiable
Every experiment must be reproducible from a single command. Seed random generators. Log hyperparameters alongside results.

---

## Repository Structure

```
.
├── CLAUDE.md                  # This file
├── README.md                  # Human-facing overview
├── .claude/
│   └── settings.json          # Claude Code permissions & hooks
├── sources/                   # Raw, immutable input documents (never edit)
├── wiki/                      # LLM-maintained knowledge base
│   ├── schema.md              # Page conventions and templates
│   ├── index.md               # Content catalog (updated on every ingest)
│   ├── log.md                 # Append-only operation log
│   ├── concepts/              # Idea / technique pages
│   ├── entities/              # Person / org / tool pages
│   ├── projects/              # Paper / codebase / product pages
│   └── qa/                    # Filed Q&A answers
├── src/                       # Application source code
├── tests/                     # Tests
├── scripts/
│   └── wiki/
│       ├── ingest.py          # Prepare ingest prompt for a source file
│       ├── query.py           # Prepare query prompt against the wiki
│       └── lint.py            # Static health-check; --fix prints fix prompt
└── docs/                      # Additional documentation
```

---

## LLM Wiki

This repository contains a persistent, LLM-maintained knowledge base in `wiki/`.
Inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

### Core idea

> The wiki is a compounding artifact. Each ingest makes it richer.
> The LLM handles bookkeeping; the human handles curation.

Three layers:

| Layer | Location | Mutability |
|-------|----------|------------|
| Raw sources | `sources/` | **Immutable** — never edit |
| Wiki pages | `wiki/` | LLM-maintained markdown |
| Schema | `wiki/schema.md` + this file | Human-curated |

### Three operations

#### 1. Ingest
Add a new source and update relevant wiki pages.

```bash
python scripts/wiki/ingest.py sources/my-paper.pdf
```

Paste the printed prompt into Claude Code. Claude will:
- Update or create wiki pages
- Add cross-references and relationships
- Update `wiki/index.md`
- Append to `wiki/log.md`

#### 2. Query
Ask a question and get an answer grounded in the wiki.

```bash
# Answer only
python scripts/wiki/query.py "What is RLHF?"

# Answer and file it as a Q&A page
python scripts/wiki/query.py "What is RLHF?" --file-answer
```

#### 3. Lint
Check the wiki for broken links, orphans, schema drift, and empty stubs.

```bash
python scripts/wiki/lint.py          # report
python scripts/wiki/lint.py --fix    # report + print LLM fix prompt
```

### AI agent rules for wiki edits

1. **Read `wiki/schema.md` first.** Every page must follow the templates.
2. **Cite sources.** Every factual claim needs a Sources entry linking to `sources/`.
3. **Use `[[Page Name]]` for internal links.** Never use relative paths for cross-references.
4. **Append-only log.** Add new entries to the top of `wiki/log.md`. Never edit past entries.
5. **Contradiction policy.** Never silently discard a claim. Flag conflicts with `> ⚠️ Contradiction:`.
6. **Low-confidence claims.** Mark inline with `[low confidence]` and set the confidence tier.
7. **Update the index.** After any create/update, refresh the relevant row in `wiki/index.md`.

---

## Commands

> Fill in the actual commands for this project.

```bash
# Install dependencies
# e.g. pip install -e ".[dev]"  OR  npm install

# Run tests
# e.g. pytest  OR  npm test

# Lint / format
# e.g. ruff check . && ruff format --check .  OR  eslint src/

# Run the app / main entry point
# e.g. python src/main.py
```

---

## Coding Standards

- **Naming**: snake_case for Python, camelCase for JS/TS. No abbreviations except universally known ones (`lr`, `idx`, `cfg`).
- **Functions**: one function = one job. If you need "and" in the name, split it.
- **Comments**: write *why*, not *what*. Assume the reader can read the language.
- **Magic numbers**: none. Name every constant.
- **Logging**: use structured logging, not `print`. Remove debug prints before committing.
- **Types**: annotate all public function signatures.

---

## Testing

- Every new behavior gets a test. Tests live in `tests/` and mirror the `src/` structure.
- Unit tests must be fast (< 1 s each). Slow tests go in `tests/integration/`.
- CI runs `pytest -x` — fail fast, fix the first red test before continuing.
- Do not mock things you own. Only mock external I/O (network, disk, time).

---

## Git Workflow

- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`
- Commit messages: imperative mood, present tense. Max 72 chars on subject line.
  - Good: `add cosine LR scheduler`
  - Bad: `added scheduler and also fixed a bug and refactored the training loop`
- One logical change per commit. If the diff requires "and" to describe, split the commit.
- Never force-push to `main`.
- Every PR needs a passing CI run before merge.

---

## AI Agent Instructions

When working in this repo, an AI agent (Claude, Codex, etc.) must:

1. **Read before writing.** Understand what already exists before adding anything.
2. **Minimal diffs.** Make the smallest change that satisfies the requirement.
3. **No orphan code.** Don't add code that nothing calls. Don't leave TODO stubs without issues filed.
4. **Run the tests.** After any code change, run the test suite and fix failures before declaring done.
5. **No silent assumptions.** If a requirement is ambiguous, surface the ambiguity in a comment or ask before guessing.
6. **Prefer plain Python/JS.** Reach for a new dependency only when the alternative would be > 50 lines of non-trivial code.
7. **Reproducibility.** Any script or experiment must be runnable from the repo root with no undocumented environment setup.

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| *(none yet)* | | |

> Add variables here as they are introduced.

---

## Known Gotchas

> Document non-obvious behavior, subtle bugs already fixed, or surprising constraints here as the project evolves.
