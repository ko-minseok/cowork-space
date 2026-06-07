#!/usr/bin/env python3
"""
ingest.py — Add a source file to the wiki.

Usage:
    python scripts/wiki/ingest.py <source_file_or_url> [--dry-run]

What it does:
1. Copies / downloads the source into sources/
2. Prints a structured prompt for the LLM to process the source and
   update relevant wiki pages.

The LLM (not this script) performs the actual wiki edits.
This script is a harness that prepares context and prints instructions.
"""

import argparse
import datetime
import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO_ROOT / "sources"
WIKI_DIR = REPO_ROOT / "wiki"


def fetch_source(src: str) -> Path:
    """Download URL or copy local file into sources/. Returns the dest path."""
    SOURCES_DIR.mkdir(exist_ok=True)
    if src.startswith("http://") or src.startswith("https://"):
        name = src.split("/")[-1].split("?")[0] or "source"
        dest = SOURCES_DIR / name
        print(f"[ingest] Downloading {src} → {dest}", file=sys.stderr)
        urllib.request.urlretrieve(src, dest)
    else:
        src_path = Path(src)
        if not src_path.exists():
            sys.exit(f"[ingest] File not found: {src}")
        dest = SOURCES_DIR / src_path.name
        if dest != src_path:
            shutil.copy2(src_path, dest)
        print(f"[ingest] Copied {src_path} → {dest}", file=sys.stderr)
    return dest


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def existing_wiki_pages() -> list[str]:
    pages = []
    for p in sorted(WIKI_DIR.rglob("*.md")):
        if p.name in ("log.md", "schema.md"):
            continue
        pages.append(str(p.relative_to(WIKI_DIR)))
    return pages


def build_prompt(source_path: Path, dry_run: bool) -> str:
    today = datetime.date.today().isoformat()
    rel = source_path.relative_to(REPO_ROOT)
    pages = existing_wiki_pages()
    pages_list = "\n".join(f"  - wiki/{p}" for p in pages) if pages else "  (none yet)"

    action = "[DRY RUN — do not write files]" if dry_run else "Write the changes to disk."

    return f"""
=== LLM INGEST TASK ===

Date: {today}
Source file: {rel}
Source hash: {file_hash(source_path)}

Read the source file at `{rel}` carefully.

Then do the following, following the conventions in `wiki/schema.md`:

1. IDENTIFY which existing wiki pages are relevant to this source.
   Existing pages:
{pages_list}

2. UPDATE each relevant page:
   - Add or revise factual claims supported by this source.
   - Add a Sources entry: `- [{source_path.name}]({rel}) — ingested {today}`
   - Update cross-references / Relationships sections.
   - Flag contradictions with existing content using the schema's contradiction policy.

3. CREATE new pages for any significant concept, entity, or project in the source
   that does not yet have a page. Follow the page-type templates in `wiki/schema.md`.

4. UPDATE `wiki/index.md`:
   - Add or refresh rows for every page you created or modified.

5. APPEND to `wiki/log.md` (at the top, below the comment marker):
   ```
   ## {today} HH:MM — ingest — {source_path.name}
   Pages affected: <comma-separated list>
   ```

{action}
=== END TASK ===
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a source into the LLM wiki.")
    parser.add_argument("source", help="Local file path or URL to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without copying source")
    args = parser.parse_args()

    if args.dry_run:
        raw = Path(args.source) if not args.source.startswith("http") else SOURCES_DIR / "preview"
        source_path = raw.resolve()
    else:
        source_path = fetch_source(args.source)

    print(build_prompt(source_path, args.dry_run))


if __name__ == "__main__":
    main()
