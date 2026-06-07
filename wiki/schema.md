# Wiki Schema

This file defines the conventions every wiki page must follow.
Read this before creating or editing any page in `wiki/`.

---

## Page types

### Concept page (`wiki/concepts/<slug>.md`)
An idea, technique, algorithm, or theory.

```markdown
# <Concept Name>

> One-sentence definition.

## What it is
...

## Why it matters
...

## Key properties / variants
...

## Relationships
- related: [[Other Concept]]
- contrast: [[Contrasting Concept]]
- used-by: [[Project or Entity]]

## Sources
- [Title](../sources/<file>) — ingested YYYY-MM-DD
```

### Entity page (`wiki/entities/<slug>.md`)
A person, organization, tool, model, or product.

```markdown
# <Entity Name>

> One-sentence description (role / what it does).

## Overview
...

## Key contributions / features
...

## Relationships
- affiliated-with: [[Organization]]
- created: [[Project]]
- uses: [[Concept]]

## Sources
- [Title](../sources/<file>) — ingested YYYY-MM-DD
```

### Project page (`wiki/projects/<slug>.md`)
A paper, codebase, product, or initiative being actively tracked.

```markdown
# <Project Name>

> One-sentence description.

## Status
`active | archived | unknown` — as of YYYY-MM-DD

## What it does
...

## Key results / metrics
...

## Open questions
- ...

## Relationships
- authors: [[Person]]
- builds-on: [[Concept]]
- competes-with: [[Project]]

## Sources
- [Title](../sources/<file>) — ingested YYYY-MM-DD
```

### Q&A page (`wiki/qa/<slug>.md`)
A question asked and answered from the wiki. Filed when the answer is non-trivial.

```markdown
# Q: <question>

**Asked**: YYYY-MM-DD  
**Confidence**: high | medium | low

## Answer
...

## Evidence
- [[Page]] — supports because ...

## Caveats
...

## Sources
- [Title](../sources/<file>)
```

---

## Linking conventions

- Internal links: `[[Page Title]]` resolves to the slug in the same or any subdirectory.
- Source citations: always link to the file in `sources/` with the ingest date.
- Do not link to external URLs inside page bodies — put URLs only in the Sources section.

---

## Slug rules

- Lowercase, hyphen-separated: `transformer-attention.md`
- No dates in slugs (dates go in `log.md` and in the Sources section).
- Prefer specificity: `attention-mechanism.md` over `attention.md`.

---

## Confidence tiers

Used in Q&A pages and optionally in factual claims:

| Tier | Meaning |
|------|---------|
| `high` | Multiple independent sources agree |
| `medium` | Single reliable source or strong inference |
| `low` | Speculative, single weak source, or LLM-inferred without citation |

Low-confidence claims must be marked `[low confidence]` inline.

---

## Contradiction policy

- For **factual** contradictions: flag with `> ⚠️ Contradiction: ...` block and record both claims with sources.
- For **interpretive** disagreements: preserve both perspectives under `## Perspectives`.
- Never silently discard a claim to resolve a contradiction.
