#!/usr/bin/env python3
"""
run_eval.py — Test whether a skill description triggers correctly.

Runs each eval case through `claude -p` and checks if the skill was invoked.

Usage:
    python scripts/skill-creator/run_eval.py <evals.json> --skill-dir <skill-dir>
    python scripts/skill-creator/run_eval.py <evals.json> --skill-dir <skill-dir> \
        --workers 4 --timeout 30 --threshold 0.7
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_skill_md

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"


def run_single_query(
    prompt: str,
    skill_name: str,
    skill_dir: Path,
    timeout: int,
    description_override: str | None,
) -> bool:
    """Run one query and return True if the skill was triggered."""
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_skill = tmp_dir / skill_name
    tmp_skill.mkdir()

    try:
        # Copy skill, optionally overriding description
        src_skill = skill_dir / "SKILL.md"
        if description_override:
            name, _, content = parse_skill_md(skill_dir)
            end = content.find("\n---", 3)
            new_fm = content[3:end]
            # Replace description line(s)
            lines = new_fm.splitlines()
            out_lines = []
            skip = False
            for line in lines:
                if line.startswith("description:"):
                    out_lines.append(f"description: {description_override}")
                    skip = True
                elif skip and (line.startswith(" ") or line.strip() == ""):
                    continue
                else:
                    skip = False
                    out_lines.append(line)
            body = content[end + 4:]
            new_content = "---\n" + "\n".join(out_lines) + "\n---" + body
            (tmp_skill / "SKILL.md").write_text(new_content)
        else:
            shutil.copy2(src_skill, tmp_skill / "SKILL.md")

        env = {**os.environ, "CLAUDE_COMMANDS_DIR": str(tmp_dir)}
        env.pop("CLAUDECODE", None)  # allow nesting

        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=REPO_ROOT,
        )
        output = result.stdout + result.stderr

        # Check if skill was triggered (tool_use with skill name in input)
        triggered = skill_name in output and "tool_use" in output
        # Fallback: simpler check
        if not triggered:
            triggered = f"/{skill_name}" in output or skill_name.replace("-", "_") in output

        return triggered

    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        print("[run_eval] 'claude' CLI not found — is Claude Code installed?", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_eval(
    evals_path: Path,
    skill_dir: Path,
    workers: int = 2,
    timeout: int = 30,
    threshold: float = 0.5,
    description_override: str | None = None,
) -> dict:
    evals = json.loads(evals_path.read_text())
    skill_name = evals.get("skill", skill_dir.name)
    cases = evals.get("cases", [])

    trigger_cases = [c for c in cases if c.get("should_trigger", True)]
    no_trigger_cases = [c for c in cases if not c.get("should_trigger", True)]

    results = {}

    def _run(case: dict, expected: bool) -> tuple[str, bool, bool]:
        triggered = run_single_query(
            case["prompt"], skill_name, skill_dir, timeout, description_override
        )
        return case["id"], triggered, expected

    all_cases = [(c, True) for c in trigger_cases] + [(c, False) for c in no_trigger_cases]

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run, case, expected): case["id"]
            for case, expected in all_cases
        }
        for future in as_completed(futures):
            case_id, triggered, expected = future.result()
            results[case_id] = {"triggered": triggered, "expected": expected, "correct": triggered == expected}

    total = len(results)
    passed = sum(1 for r in results.values() if r["correct"])
    pass_rate = passed / total if total else 0.0

    summary = {
        "skill": skill_name,
        "total": total,
        "passed": passed,
        "pass_rate": pass_rate,
        "threshold": threshold,
        "ok": pass_rate >= threshold,
        "per_case": results,
    }

    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evals", help="Path to evals.json")
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--description", help="Override skill description for testing")
    args = parser.parse_args()

    result = run_eval(
        Path(args.evals),
        Path(args.skill_dir),
        workers=args.workers,
        timeout=args.timeout,
        threshold=args.threshold,
        description_override=args.description,
    )
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
