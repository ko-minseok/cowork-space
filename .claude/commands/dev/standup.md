Generate a standup summary from recent git activity.

Steps:
1. Run `git log --oneline --since="yesterday" --author="$(git config user.name)"`.
   If $ARGUMENTS is provided, use it as the --since value (e.g. "2 days ago", "2026-06-01").
2. Run `git diff HEAD~5..HEAD --stat` to get a file-level summary.
3. Check for open items:
   - Uncommitted changes: `git status --short`
   - Any TODO/FIXME added in recent diffs: `git diff HEAD~5..HEAD | grep -E "TODO|FIXME"`
4. Compose a standup in this format:

   **Yesterday / Since <date>**
   - <bullet per logical theme, not per commit>

   **Today**
   - <inferred next steps from open TODOs and in-progress work>

   **Blockers**
   - <anything with FIXME or uncommitted work that looks stuck>

Keep each bullet to one line. No filler phrases ("worked on", "made progress on").

Usage: /dev:standup
       /dev:standup 2 days ago
