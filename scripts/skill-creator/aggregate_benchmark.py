#!/usr/bin/env python3
"""
aggregate_benchmark.py — Aggregate grading results across multiple eval runs.

Produces benchmark.json and benchmark.md comparing with_skill vs without_skill.

Usage:
    python scripts/skill-creator/aggregate_benchmark.py <benchmark-dir> [--skill-name NAME]

Expected directory layout:
    benchmark-dir/
      with_skill/
        eval-1/grading.json
        eval-2/grading.json
        ...
      without_skill/
        eval-1/grading.json
        ...
"""

import argparse
import json
import math
import sys
from pathlib import Path


def load_run_metrics(run_dir: Path) -> dict | None:
    grading_file = run_dir / "grading.json"
    timing_file = run_dir / "timing.json"

    if not grading_file.exists():
        return None

    grading = json.loads(grading_file.read_text())
    pass_rate = grading.get("pass_rate", 0.0)

    timing = {}
    if timing_file.exists():
        timing = json.loads(timing_file.read_text())

    duration = timing.get("duration_ms", 0) / 1000
    if not duration:
        executor_s = grading.get("timing", {}).get("executor_seconds", 0)
        grader_s = grading.get("timing", {}).get("grader_seconds", 0)
        duration = executor_s + grader_s

    tokens = timing.get("total_tokens", 0)

    return {"pass_rate": pass_rate, "time_seconds": duration, "tokens": tokens}


def stats(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return {
        "mean": round(mean, 4),
        "std": round(math.sqrt(variance), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "n": n,
    }


def load_config(config_dir: Path) -> dict:
    runs = []
    # Support eval-N/ and runs/ layouts
    candidates = sorted(config_dir.glob("eval-*/")) + sorted((config_dir / "runs").glob("*/")) \
        if (config_dir / "runs").exists() else sorted(config_dir.glob("eval-*/"))

    for run_dir in candidates:
        m = load_run_metrics(run_dir)
        if m:
            runs.append(m)

    return {
        "runs": len(runs),
        "pass_rate": stats([r["pass_rate"] for r in runs]),
        "time_seconds": stats([r["time_seconds"] for r in runs]),
        "tokens": stats([r["tokens"] for r in runs]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark_dir", help="Root benchmark directory")
    parser.add_argument("--skill-name", default="")
    args = parser.parse_args()

    bench_dir = Path(args.benchmark_dir)
    configs: dict[str, dict] = {}

    for config_dir in sorted(bench_dir.iterdir()):
        if config_dir.is_dir() and not config_dir.name.startswith("."):
            configs[config_dir.name] = load_config(config_dir)

    # Compute deltas: primary config vs "without_skill" baseline
    baseline_key = "without_skill"
    primary_key = "with_skill"
    deltas: dict = {}
    if primary_key in configs and baseline_key in configs:
        for metric in ("pass_rate", "time_seconds", "tokens"):
            pm = configs[primary_key][metric]["mean"]
            bm = configs[baseline_key][metric]["mean"]
            deltas[metric] = round(pm - bm, 4)

    benchmark = {
        "skill": args.skill_name,
        "configs": configs,
        "deltas": deltas,
    }

    out_json = bench_dir / "benchmark.json"
    out_md = bench_dir / "benchmark.md"

    out_json.write_text(json.dumps(benchmark, indent=2))

    # Markdown report
    md_lines = [f"# Benchmark: {args.skill_name or bench_dir.name}", ""]
    for cfg_name, cfg in configs.items():
        md_lines += [
            f"## {cfg_name} (n={cfg['runs']})",
            "",
            "| Metric | Mean | Std | Min | Max |",
            "|--------|------|-----|-----|-----|",
        ]
        for metric in ("pass_rate", "time_seconds", "tokens"):
            s = cfg[metric]
            md_lines.append(f"| {metric} | {s['mean']} | {s['std']} | {s['min']} | {s['max']} |")
        md_lines.append("")

    if deltas:
        md_lines += [
            "## Deltas (with_skill − without_skill)", "",
            "| Metric | Delta |",
            "|--------|-------|",
        ]
        for k, v in deltas.items():
            md_lines.append(f"| {k} | {v:+.4f} |")

    out_md.write_text("\n".join(md_lines))
    print(f"benchmark.json → {out_json}")
    print(f"benchmark.md   → {out_md}")
    print(json.dumps(benchmark, indent=2))


if __name__ == "__main__":
    main()
