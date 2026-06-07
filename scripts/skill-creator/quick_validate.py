#!/usr/bin/env python3
"""Validate a skill directory's SKILL.md against the skill-creator schema."""

import re
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_skill_md

ALLOWED_FIELDS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return [f"SKILL.md not found in {skill_dir}"]

    try:
        name, description, content = parse_skill_md(skill_dir)
    except ValueError as e:
        return [str(e)]

    # Parse raw frontmatter for field validation
    end = content.find("\n---", 3)
    frontmatter_text = content[3:end].strip()
    try:
        fm = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as e:
        return [f"Invalid YAML in frontmatter: {e}"]

    # Required fields
    if not name:
        errors.append("Missing required field: name")
    else:
        if len(name) > 64:
            errors.append(f"name too long ({len(name)} > 64 chars)")
        if not NAME_RE.match(name):
            errors.append(f"name must be kebab-case [a-z0-9-]: got '{name}'")

    if not description:
        errors.append("Missing required field: description")
    else:
        if len(description) > 1024:
            errors.append(f"description too long ({len(description)} > 1024 chars)")
        if "<" in description or ">" in description:
            errors.append("description must not contain angle brackets")

    # Unexpected fields
    for field in fm:
        if field not in ALLOWED_FIELDS:
            errors.append(f"Unexpected frontmatter field: '{field}'")

    # Optional field constraints
    if "compatibility" in fm and len(str(fm["compatibility"])) > 500:
        errors.append("compatibility field too long (> 500 chars)")

    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: quick_validate.py <skill-directory>", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1])
    errors = validate(skill_dir)

    if errors:
        print(f"✗ {skill_dir.name}: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"✓ {skill_dir.name}: valid")


if __name__ == "__main__":
    main()
