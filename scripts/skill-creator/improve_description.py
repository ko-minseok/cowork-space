#!/usr/bin/env python3
"""
improve_description.py — Use Claude to improve a skill's description based on eval failures.

Usage:
    python scripts/skill-creator/improve_description.py \
        --skill-dir .claude/commands/my-skill \
        --eval-results eval_results.json \
        --history history.json \
        --train-score 0.60 --test-score 0.55
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_skill_md

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_DESC_LEN = 1024


def build_prompt(
    name: str,
    current_description: str,
    skill_content: str,
    eval_results: dict,
    history: list[dict],
    train_score: float,
    test_score: float,
) -> str:
    failed_triggers = [
        cid for cid, r in eval_results.get("per_case", {}).items()
        if not r["correct"] and r["expected"]
    ]
    false_triggers = [
        cid for cid, r in eval_results.get("per_case", {}).items()
        if not r["correct"] and not r["expected"]
    ]

    history_text = ""
    if history:
        history_text = "\n\nPrevious attempts (do not repeat these approaches):\n"
        for h in history[-5:]:
            history_text += f"- v{h['version']}: train={h['train_pass_rate']:.0%} test={h['test_pass_rate']:.0%}\n"
            history_text += f"  description: {h['description'][:200]}\n"

    return f"""You are improving the trigger description for a Claude Code skill named '{name}'.

Current performance:
- Train pass rate: {train_score:.0%}
- Test pass rate: {test_score:.0%}

Current description:
{current_description}

Full skill content (for context):
{skill_content[:2000]}

Failed to trigger (should have triggered but didn't):
{json.dumps(failed_triggers, indent=2)}

False triggers (triggered but shouldn't have):
{json.dumps(false_triggers, indent=2)}
{history_text}

Write an improved description that:
1. Better matches the cases that failed to trigger
2. Avoids triggering on the false trigger cases
3. Is ≤ {MAX_DESC_LEN} characters
4. Uses a structurally different approach from previous attempts

Respond with JSON only:
{{"description": "new description here"}}"""


def improve(
    skill_dir: Path,
    eval_results: dict,
    history: list[dict],
    train_score: float,
    test_score: float,
    log_dir: Path | None = None,
) -> str:
    name, current_desc, content = parse_skill_md(skill_dir)
    prompt = build_prompt(name, current_desc, content, eval_results, history, train_score, test_score)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "improve_prompt.txt").write_text(prompt)

    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )

    raw = result.stdout.strip()
    if log_dir:
        (log_dir / "improve_response.txt").write_text(raw)

    try:
        data = json.loads(raw)
        new_desc = data.get("description", "")
    except json.JSONDecodeError:
        # Try to extract JSON from mixed output
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            new_desc = data.get("description", "")
        else:
            raise ValueError(f"Could not parse JSON from Claude response: {raw[:200]}")

    if len(new_desc) > MAX_DESC_LEN:
        # Ask for a shorter version
        shorten_prompt = (
            f"The description you wrote is {len(new_desc)} characters, "
            f"but the limit is {MAX_DESC_LEN}. Shorten it without losing meaning. "
            f'Respond with JSON only: {{"description": "..."}}\n\nOriginal:\n{new_desc}'
        )
        result2 = subprocess.run(
            ["claude", "-p", shorten_prompt, "--output-format", "json"],
            capture_output=True, text=True, env=env, cwd=REPO_ROOT,
        )
        data2 = json.loads(result2.stdout.strip())
        new_desc = data2.get("description", new_desc)[:MAX_DESC_LEN]

    return new_desc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--eval-results", required=True, help="JSON file from run_eval.py")
    parser.add_argument("--history", default=None, help="JSON file with iteration history")
    parser.add_argument("--train-score", type=float, default=0.0)
    parser.add_argument("--test-score", type=float, default=0.0)
    parser.add_argument("--log-dir", default=None)
    args = parser.parse_args()

    eval_results = json.loads(Path(args.eval_results).read_text())
    history = json.loads(Path(args.history).read_text()).get("iterations", []) if args.history else []
    log_dir = Path(args.log_dir) if args.log_dir else None

    new_desc = improve(
        Path(args.skill_dir), eval_results, history,
        args.train_score, args.test_score, log_dir,
    )
    print(json.dumps({"description": new_desc}, indent=2))


if __name__ == "__main__":
    main()
