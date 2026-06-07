Run the wiki health-check and fix all reported issues.

Steps:
1. Run `python scripts/wiki/lint.py --fix` and capture its output.
2. The output has two parts:
   a. A human-readable report of issues found.
   b. An LLM task prompt listing what to fix — execute it:
      - Fix orphan pages (add inbound links from related pages).
      - Fix broken [[links]] (correct the target or remove the link).
      - Add missing pages to `wiki/index.md`.
      - Expand or delete empty stub pages.
      - Add missing sections per `wiki/schema.md` templates.
3. After fixes, re-run `python scripts/wiki/lint.py` to confirm zero issues.
4. Commit all changes: `wiki: lint fixes`

If lint reports zero issues, say so and stop — do not make unnecessary edits.

Usage: /wiki:lint
