Run the test suite and report results clearly.

Steps:
1. Read `CLAUDE.md` → Commands section to find the test command.
   If not yet filled in, look for common patterns: `pytest`, `npm test`, `make test`.
2. Run the test command. Capture stdout and stderr.
3. Report:
   - PASS count, FAIL count, ERROR count.
   - For each failure: file, test name, error message, relevant line.
   - Total wall-clock time.
4. If failures exist:
   - Diagnose each failure: is it a test bug or a source bug?
   - For source bugs: propose a minimal fix. Do not fix without confirmation.
   - For test bugs: explain why and propose the correction.
5. If $ARGUMENTS is provided, run only matching tests:
   e.g. `pytest -k $ARGUMENTS` or equivalent.

Do not modify any file during this skill — report only.

Usage: /dev:test
       /dev:test test_ingest
