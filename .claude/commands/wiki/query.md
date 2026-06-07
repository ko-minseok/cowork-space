Answer a question grounded in the wiki, then optionally file the answer.

Steps:
1. Run `python scripts/wiki/query.py $ARGUMENTS` and capture its output.
2. The output is a structured task prompt — execute it:
   - Read the wiki pages it identifies as relevant.
   - Synthesize a direct answer with [[Page]] citations.
   - State confidence tier (high / medium / low) with justification.
   - Note any gaps or contradictions in the wiki.
3. If the prompt instructs filing the answer (--file-answer flag was passed):
   - Write the Q&A page to `wiki/qa/<slug>.md`.
   - Add a row to `wiki/index.md` under Q&A.
   - Append a log entry to `wiki/log.md`.
   - Commit: `wiki: file answer for "<question>"`

Usage: /wiki:query What is RLHF?
       /wiki:query --file-answer What is the difference between SFT and RLHF?
