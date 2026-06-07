#!/usr/bin/env python3
"""
package_skill.py — Package a skill directory into a distributable .skill ZIP archive.

Usage:
    python scripts/skill-creator/package_skill.py <skill-dir> [output-dir]

Output: <output-dir>/<skill-name>.skill
"""

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from quick_validate import validate
from utils import parse_skill_md

EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git"}
EXCLUDE_PATTERNS = {"*.pyc", ".DS_Store", "*.egg-info"}
EXCLUDE_ROOT_DIRS = {"evals"}  # excluded only at root level


def should_exclude(path: Path, skill_dir: Path) -> bool:
    rel = path.relative_to(skill_dir)
    parts = rel.parts

    for pat in EXCLUDE_PATTERNS:
        if path.match(pat):
            return True

    for part in parts:
        if part in EXCLUDE_DIRS:
            return True

    # Exclude root-level evals/ directory
    if parts and parts[0] in EXCLUDE_ROOT_DIRS:
        return True

    return False


def package_skill(skill_dir: Path, output_dir: Path) -> Path:
    if not skill_dir.exists():
        sys.exit(f"Error: skill directory not found: {skill_dir}")

    if not (skill_dir / "SKILL.md").exists():
        sys.exit(f"Error: SKILL.md not found in {skill_dir}")

    errors = validate(skill_dir)
    if errors:
        print("Validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    name, _, _ = parse_skill_md(skill_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{name}.skill"

    included: list[str] = []
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(skill_dir.rglob("*")):
            if file.is_file() and not should_exclude(file, skill_dir):
                arcname = file.relative_to(skill_dir.parent)
                zf.write(file, arcname)
                included.append(str(arcname))

    print(f"✓ Packaged: {out_path}")
    print(f"  {len(included)} file(s) included:")
    for f in included:
        print(f"    {f}")

    return out_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: package_skill.py <skill-dir> [output-dir]", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./dist")
    package_skill(skill_dir, output_dir)


if __name__ == "__main__":
    main()
