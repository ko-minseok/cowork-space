Create a clean, well-scoped git commit following this repository's conventions.

Steps:
1. Run `git diff --staged` and `git status` to see what is staged.
   If nothing is staged, run `git diff` to see unstaged changes and ask which files to include.
2. Analyze the diff:
   - Identify the logical scope of the change (one concern only).
   - If the diff contains multiple unrelated concerns, say so and stop — ask the user to stage them separately.
3. Draft a commit message:
   - Subject line: imperative mood, present tense, ≤ 72 chars.
   - Prefix with type: `feat:` `fix:` `chore:` `docs:` `test:` `refactor:` `wiki:`
   - Body (if needed): explain WHY, not what. Wrap at 72 chars.
   - No "and" in the subject — one change, one commit.
4. Show the draft message and ask for confirmation before committing.
5. On confirmation, commit with that message appended with the session URL.

If $ARGUMENTS is provided, use it as the commit message subject directly (skip drafting).

Usage: /dev:commit
       /dev:commit fix: handle empty query string in query.py
