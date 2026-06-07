#!/usr/bin/env python3
"""
lint.py — Health-check the wiki and print a structured LLM prompt to fix issues.

Usage:
    python scripts/wiki/lint.py            # report only
    python scripts/wiki/lint.py --fix      # print fix prompt for the LLM

Checks performed (statically, without an LLM):
  1. Orphan pages   — wiki pages with no inbound [[links]]
  2. Broken links   — [[Page]] references that match no existing file
  3. Missing index  — pages not listed in wiki/index.md
  4. Empty pages    — pages with < 50 characters of content
  5. Schema drift   — pages missing required sections for their type
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = REPO_ROOT / "wiki"

REQUIRED_SECTIONS = {
    "concepts": ["## What it is", "## Relationships", "## Sources"],
    "entities": ["## Overview", "## Relationships", "## Sources"],
    "projects": ["## What it does", "## Relationships", "## Sources"],
    "qa": ["## Answer", "## Evidence"],
}

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def all_pages() -> dict[str, Path]:
    """Return {slug: path} for every .md under wiki/ (except special files)."""
    special = {"log.md", "schema.md", "index.md"}
    pages: dict[str, Path] = {}
    for p in WIKI_DIR.rglob("*.md"):
        if p.name in special:
            continue
        slug = p.stem.lower()
        pages[slug] = p
    return pages


def extract_links(text: str) -> list[str]:
    return [m.lower().replace(" ", "-") for m in LINK_RE.findall(text)]


def check_orphans(pages: dict[str, Path]) -> list[str]:
    inbound: dict[str, int] = {slug: 0 for slug in pages}
    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        for link in extract_links(text):
            if link in inbound and link != slug:
                inbound[link] += 1
    # Also count links from index.md
    index = WIKI_DIR / "index.md"
    if index.exists():
        for link in extract_links(index.read_text(encoding="utf-8")):
            if link in inbound:
                inbound[link] += 1
    return [slug for slug, count in inbound.items() if count == 0]


def check_broken_links(pages: dict[str, Path]) -> dict[str, list[str]]:
    broken: dict[str, list[str]] = {}
    for slug, path in pages.items():
        text = path.read_text(encoding="utf-8")
        bad = [link for link in extract_links(text) if link not in pages]
        if bad:
            broken[slug] = bad
    return broken


def check_missing_from_index(pages: dict[str, Path]) -> list[str]:
    index = WIKI_DIR / "index.md"
    if not index.exists():
        return list(pages.keys())
    index_text = index.read_text(encoding="utf-8").lower()
    return [slug for slug in pages if slug not in index_text]


def check_empty(pages: dict[str, Path]) -> list[str]:
    return [slug for slug, path in pages.items() if len(path.read_text(encoding="utf-8").strip()) < 50]


def check_schema_drift(pages: dict[str, Path]) -> dict[str, list[str]]:
    drift: dict[str, list[str]] = {}
    for slug, path in pages.items():
        parent = path.parent.name  # concepts / entities / projects / qa
        required = REQUIRED_SECTIONS.get(parent, [])
        text = path.read_text(encoding="utf-8")
        missing = [sec for sec in required if sec not in text]
        if missing:
            drift[slug] = missing
    return drift


def report(issues: dict) -> None:
    total = sum(
        len(v) if isinstance(v, (list, dict)) else 1
        for v in issues.values()
        if v
    )
    if total == 0:
        print("✓ Wiki is healthy — no issues found.")
        return

    print(f"⚠  {total} issue(s) found:\n")

    if issues["orphans"]:
        print("ORPHAN PAGES (no inbound links):")
        for s in issues["orphans"]:
            print(f"  - {s}")

    if issues["broken_links"]:
        print("\nBROKEN LINKS:")
        for slug, links in issues["broken_links"].items():
            print(f"  - {slug}: {', '.join(links)}")

    if issues["missing_from_index"]:
        print("\nMISSING FROM index.md:")
        for s in issues["missing_from_index"]:
            print(f"  - {s}")

    if issues["empty"]:
        print("\nEMPTY / STUB PAGES:")
        for s in issues["empty"]:
            print(f"  - {s}")

    if issues["schema_drift"]:
        print("\nSCHEMA DRIFT (missing required sections):")
        for slug, sections in issues["schema_drift"].items():
            print(f"  - {slug}: missing {', '.join(sections)}")


def build_fix_prompt(issues: dict) -> str:
    lines = ["=== LLM LINT-FIX TASK ===", "", "Fix the following wiki health issues:"]

    if issues["orphans"]:
        lines.append(f"\n1. ORPHAN PAGES — add inbound [[links]] from related pages:")
        for s in issues["orphans"]:
            lines.append(f"   - {s}")

    if issues["broken_links"]:
        lines.append(f"\n2. BROKEN LINKS — fix or remove each broken [[link]]:")
        for slug, links in issues["broken_links"].items():
            lines.append(f"   - {slug}: {', '.join(links)}")

    if issues["missing_from_index"]:
        lines.append(f"\n3. MISSING FROM INDEX — add rows to wiki/index.md:")
        for s in issues["missing_from_index"]:
            lines.append(f"   - {s}")

    if issues["empty"]:
        lines.append(f"\n4. EMPTY PAGES — expand or delete each stub:")
        for s in issues["empty"]:
            lines.append(f"   - {s}")

    if issues["schema_drift"]:
        lines.append(f"\n5. SCHEMA DRIFT — add missing sections per wiki/schema.md:")
        for slug, sections in issues["schema_drift"].items():
            lines.append(f"   - {slug}: add {', '.join(sections)}")

    lines += [
        "",
        "Follow wiki/schema.md conventions for all edits.",
        "Append a log entry to wiki/log.md when done.",
        "=== END TASK ===",
    ]
    return "\n".join(lines)


def main() -> None:
    fix = "--fix" in sys.argv

    pages = all_pages()
    issues = {
        "orphans": check_orphans(pages),
        "broken_links": check_broken_links(pages),
        "missing_from_index": check_missing_from_index(pages),
        "empty": check_empty(pages),
        "schema_drift": check_schema_drift(pages),
    }

    report(issues)

    has_issues = any(issues.values())
    if fix and has_issues:
        print("\n" + build_fix_prompt(issues))
    elif fix:
        print("\n(Nothing to fix.)")

    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
