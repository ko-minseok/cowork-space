"""Shared utilities for skill-creator scripts."""

from pathlib import Path


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file and return (name, description, full_content).

    Raises ValueError if frontmatter delimiters are missing.
    """
    skill_file = skill_path / "SKILL.md" if skill_path.is_dir() else skill_path
    content = skill_file.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError(f"{skill_file}: missing opening frontmatter delimiter '---'")

    end = content.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{skill_file}: missing closing frontmatter delimiter '---'")

    frontmatter = content[3:end].strip()
    name = ""
    description_lines: list[str] = []
    in_description = False
    block_scalar = False

    for line in frontmatter.splitlines():
        if line.startswith("name:"):
            name = line[5:].strip().strip('"\'')
            in_description = False
        elif line.startswith("description:"):
            rest = line[12:].strip()
            in_description = True
            if rest in (">", "|", ">-", "|-"):
                block_scalar = True
            else:
                description_lines = [rest.strip('"\'')]
                block_scalar = False
        elif in_description and block_scalar and line.startswith(" "):
            description_lines.append(line.strip())
        else:
            in_description = False

    description = " ".join(description_lines).strip()
    return name, description, content
