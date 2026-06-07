Create a new wiki page from the correct template in wiki/schema.md.

Argument format: <type> <title>
  type: concept | entity | project | qa
  title: the page title (may include spaces)

Steps:
1. Parse $ARGUMENTS to extract type and title.
2. Derive slug: lowercase, hyphen-separated, max 60 chars.
3. Determine destination path:
   - concept → wiki/concepts/<slug>.md
   - entity  → wiki/entities/<slug>.md
   - project → wiki/projects/<slug>.md
   - qa      → wiki/qa/<slug>.md
4. Read the matching template from `wiki/schema.md`.
5. Write the new page with the template filled in:
   - Replace placeholder headings with the actual title.
   - Leave all content sections empty with a single `...` line.
   - Set Sources to `*(none yet)*`.
6. Add a row to `wiki/index.md` under the correct category, marked `stub`.
7. Append to `wiki/log.md`: `## <date> — new-page — <slug>`
8. Do NOT commit — let the user fill in content first.

Usage: /wiki:new-page concept Retrieval-Augmented Generation
       /wiki:new-page entity Andrej Karpathy
       /wiki:new-page project nanoGPT
