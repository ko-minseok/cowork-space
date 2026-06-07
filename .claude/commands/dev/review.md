Review the current diff against this repository's development philosophy.

Steps:
1. Run `git diff HEAD` (or `git diff $ARGUMENTS` if a base ref is given).
2. Read `CLAUDE.md` sections "Development Philosophy" and "Coding Standards".
3. Review the diff through Karpathy's lens — flag only real problems:

   CORRECTNESS (file if found):
   - Logic errors, off-by-one, wrong conditions
   - Unhandled edge cases at system boundaries (user input, external I/O)
   - Security issues (injection, leaked secrets, unvalidated input)

   CLARITY (flag if egregious):
   - Names that require context to decode
   - Functions doing more than one job
   - Comments that describe WHAT instead of WHY

   COMPLEXITY (flag if unnecessary):
   - Abstraction introduced for fewer than 3 concrete cases
   - Dependency added for < 50 lines of trivial code
   - Generalization before a second use case exists

   SKIP unless severe:
   - Style preferences with no clarity impact
   - Hypothetical future concerns
   - Refactoring unrelated to the change

4. Output a concise list: one finding per line, format:
   `[SEVERITY] file:line — finding — suggestion`
   SEVERITY: MUST-FIX | CONSIDER | MINOR

5. End with a one-line verdict: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION.

Usage: /dev:review
       /dev:review main..feature-branch
