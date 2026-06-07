Run the wiki ingest pipeline for the given source file or URL.

Steps:
1. Run `python scripts/wiki/ingest.py $ARGUMENTS` and capture its output.
2. The output is a structured task prompt — execute it exactly as written:
   - Read the source file it identifies.
   - Update or create wiki pages following `wiki/schema.md`.
   - Update `wiki/index.md`.
   - Append a log entry to `wiki/log.md`.
3. After all edits, run `python scripts/wiki/lint.py` and fix any issues it reports.
4. Stage and commit all changed files:
   - Message format: `wiki: ingest <source-filename>`

Usage: /wiki:ingest sources/my-paper.md
       /wiki:ingest https://example.com/article
