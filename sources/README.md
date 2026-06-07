# sources/

Raw, immutable input documents. **Never edit files in this directory.**

Files here are ingested into `wiki/` by the LLM using `scripts/wiki/ingest.py`.

## Accepted formats

- `.md` — Markdown articles, notes
- `.txt` — Plain text
- `.pdf` — Papers (convert to text before ingesting if needed)
- `.html` — Saved web pages

## Naming convention

`YYYY-MM-DD_<brief-slug>.<ext>`

Example: `2026-06-07_attention-is-all-you-need.pdf`

## Adding a source

```bash
# Local file
python scripts/wiki/ingest.py path/to/file.md

# URL
python scripts/wiki/ingest.py https://example.com/paper.pdf

# Dry run (inspect prompt without copying)
python scripts/wiki/ingest.py path/to/file.md --dry-run
```

Paste the printed prompt into your Claude Code session.
Claude will update the wiki pages and log the ingest.
