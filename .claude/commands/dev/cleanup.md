Find and remove dead code, stale comments, and orphaned files in the working tree.

Steps:
1. Identify candidates (report only — do not delete yet):

   DEAD CODE:
   - Functions/classes defined but never imported or called anywhere.
     Use: `grep -rn "def <name>\|class <name>" src/` then check for callers.
   - Commented-out code blocks (≥ 3 consecutive commented lines).

   STALE COMMENTS:
   - Comments describing WHAT (e.g. "# increment counter") — flag, don't delete.
   - TODO/FIXME older than 30 days (check `git log -S "TODO" --follow`).

   ORPHANED FILES:
   - Files in `src/` with no imports elsewhere.
   - `.gitkeep` files in directories that now have real content.
   - Empty `__init__.py` files (Python only, if package is already importable).

2. Present a checklist:
   ```
   [ ] src/utils.py:42 — dead function `_old_normalize`
   [ ] src/loader.py:18-24 — commented-out block
   [ ] src/legacy/ — directory with no callers
   ```

3. Ask which items to remove.
4. After confirmation, delete/edit only the approved items.
5. Run tests to confirm nothing broke.
6. Commit: `chore: remove dead code`

Usage: /dev:cleanup
