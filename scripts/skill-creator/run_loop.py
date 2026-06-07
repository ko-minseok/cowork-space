#!/usr/bin/env python3
"""
run_loop.py — Iteratively improve a skill description until evals pass.

Usage:
    python scripts/skill-creator/run_loop.py <evals.json> <skill-dir> [options]

Options:
    --max-iterations N    Stop after N improvement cycles (default: 5)
    --workers N           Parallel eval workers (default: 2)
    --timeout N           Seconds per eval query (default: 30)
    --threshold F         Trigger rate to consider passing (default: 0.7)
    --train-split F       Fraction of cases used for training (default: 0.7)
    --report PATH         Write HTML progress report here
    --out-dir DIR         Save results here (default: /tmp/skill-loop-<name>)
"""

import argparse
import json
import random
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import parse_skill_md
from run_eval import run_eval
from improve_description import improve
from generate_report import generate_html

REPO_ROOT = Path(__file__).resolve().parents[2]


def split_cases(cases: list[dict], train_frac: float, seed: int = 42) -> tuple[list, list]:
    """Stratified split preserving should_trigger ratio."""
    trigger = [c for c in cases if c.get("should_trigger", True)]
    no_trigger = [c for c in cases if not c.get("should_trigger", True)]
    rng = random.Random(seed)
    rng.shuffle(trigger)
    rng.shuffle(no_trigger)

    def split(lst: list) -> tuple[list, list]:
        k = max(1, int(len(lst) * train_frac))
        return lst[:k], lst[k:]

    tr_t, te_t = split(trigger)
    tr_n, te_n = split(no_trigger)
    return tr_t + tr_n, te_t + te_n


def write_description(skill_dir: Path, new_desc: str) -> None:
    name, _, content = parse_skill_md(skill_dir)
    end = content.find("\n---", 3)
    fm_lines = content[3:end].splitlines()
    out_lines = []
    skip = False
    for line in fm_lines:
        if line.startswith("description:"):
            out_lines.append(f"description: >")
            out_lines.append(f"  {new_desc}")
            skip = True
        elif skip and (line.startswith(" ") or not line.strip()):
            continue
        else:
            skip = False
            out_lines.append(line)
    body = content[end + 4:]
    new_content = "---\n" + "\n".join(out_lines) + "\n---" + body
    (skill_dir / "SKILL.md").write_text(new_content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evals", help="Path to evals.json")
    parser.add_argument("skill_dir", help="Path to skill directory")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--train-split", type=float, default=0.7)
    parser.add_argument("--report", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    evals_path = Path(args.evals)
    name, _, _ = parse_skill_md(skill_dir)

    out_dir = Path(args.out_dir) if args.out_dir else Path(f"/tmp/skill-loop-{name}")
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_evals = json.loads(evals_path.read_text())
    train_cases, test_cases = split_cases(raw_evals.get("cases", []), args.train_split)

    history: dict = {
        "started": datetime.datetime.utcnow().isoformat() + "Z",
        "skill": name,
        "best_version": 0,
        "iterations": [],
    }
    history_path = out_dir / "history.json"

    best_test = -1.0

    for iteration in range(1, args.max_iterations + 1):
        iter_dir = out_dir / f"iter-{iteration}"
        iter_dir.mkdir(exist_ok=True)

        # Eval on train split
        train_evals_path = iter_dir / "train_evals.json"
        train_evals_path.write_text(json.dumps({**raw_evals, "cases": train_cases}))
        train_result = run_eval(train_evals_path, skill_dir, args.workers, args.timeout, args.threshold)
        (iter_dir / "train_grading.json").write_text(json.dumps(train_result, indent=2))

        # Eval on test split
        test_evals_path = iter_dir / "test_evals.json"
        test_evals_path.write_text(json.dumps({**raw_evals, "cases": test_cases}))
        test_result = run_eval(test_evals_path, skill_dir, args.workers, args.timeout, args.threshold)
        (iter_dir / "test_grading.json").write_text(json.dumps(test_result, indent=2))

        train_score = train_result["pass_rate"]
        test_score = test_result["pass_rate"]

        _, current_desc, _ = parse_skill_md(skill_dir)
        entry = {
            "version": iteration,
            "description": current_desc,
            "train_pass_rate": train_score,
            "test_pass_rate": test_score,
            "parent": iteration - 1 if iteration > 1 else None,
        }
        history["iterations"].append(entry)

        if test_score > best_test:
            best_test = test_score
            history["best_version"] = iteration

        history_path.write_text(json.dumps(history, indent=2))

        print(
            f"[loop] Iteration {iteration}: train={train_score:.0%} test={test_score:.0%}",
            file=sys.stderr,
        )

        # Generate report
        if args.report:
            try:
                html = generate_html(history, skill_name=name)
                Path(args.report).write_text(html)
            except Exception:
                pass

        if train_score >= args.threshold and test_score >= args.threshold:
            print(f"[loop] Passed threshold {args.threshold:.0%} — stopping.", file=sys.stderr)
            break

        if iteration < args.max_iterations:
            new_desc = improve(
                skill_dir, train_result, history["iterations"],
                train_score, test_score, iter_dir / "improve_logs",
            )
            write_description(skill_dir, new_desc)

    print(f"[loop] Best version: {history['best_version']}")
    print(f"[loop] Results saved to: {out_dir}")
    print(json.dumps(history, indent=2))


if __name__ == "__main__":
    main()
