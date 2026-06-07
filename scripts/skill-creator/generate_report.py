#!/usr/bin/env python3
"""
generate_report.py — Render an HTML progress report from run_loop.py history JSON.

Usage:
    python scripts/skill-creator/generate_report.py history.json -o report.html
    python scripts/skill-creator/generate_report.py - -o report.html < history.json
    python scripts/skill-creator/generate_report.py history.json -o report.html --auto-refresh
"""

import argparse
import html
import json
import sys
from pathlib import Path


def _score_class(rate: float) -> str:
    if rate >= 0.8:
        return "good"
    if rate >= 0.5:
        return "ok"
    return "bad"


def generate_html(history: dict, skill_name: str = "", auto_refresh: bool = False) -> str:
    iterations = history.get("iterations", [])
    best = history.get("best_version", 0)
    train_queries: list[str] = []
    test_queries: list[str] = []

    # Derive query labels from first iteration if available
    if iterations:
        first = iterations[0]
        train_queries = [f"train-{i}" for i in range(int(len(first.get("per_case_train", {}))))]
        test_queries = [f"test-{i}" for i in range(int(len(first.get("per_case_test", {}))))]

    refresh_tag = '<meta http-equiv="refresh" content="5">' if auto_refresh else ""
    title = html.escape(f"Skill Creator — {skill_name or 'report'}")

    rows = ""
    for entry in iterations:
        v = entry["version"]
        tr = entry.get("train_pass_rate", 0)
        te = entry.get("test_pass_rate", 0)
        highlight = ' style="background:#fffbe6"' if v == best else ""
        desc_short = html.escape(entry.get("description", "")[:120])
        rows += f"""
        <tr{highlight}>
          <td>{'⭐ ' if v == best else ''}v{v}</td>
          <td class="{_score_class(tr)}">{tr:.0%}</td>
          <td class="{_score_class(te)}">{te:.0%}</td>
          <td style="font-size:0.85em;color:#555">{desc_short}</td>
        </tr>"""

    orig_desc = html.escape(iterations[0]["description"] if iterations else "")
    best_entry = next((e for e in iterations if e["version"] == best), {})
    best_desc = html.escape(best_entry.get("description", ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  {refresh_tag}
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.4rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
    th {{ background: #333; color: #fff; }}
    .good {{ color: #1a7a1a; font-weight: bold; }}
    .ok   {{ color: #a06000; }}
    .bad  {{ color: #c0001a; font-weight: bold; }}
    pre {{ background: #f6f6f6; padding: 0.75rem; border-radius: 4px; white-space: pre-wrap; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p>Best version: <strong>v{best}</strong></p>

  <h2>Original description</h2>
  <pre>{orig_desc}</pre>

  <h2>Best description</h2>
  <pre>{best_desc}</pre>

  <h2>Iteration history</h2>
  <table>
    <thead>
      <tr><th>Version</th><th>Train</th><th>Test</th><th>Description (preview)</th></tr>
    </thead>
    <tbody>{rows}
    </tbody>
  </table>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="history.json path or '-' for stdin")
    parser.add_argument("-o", "--output", required=True, help="Output HTML file")
    parser.add_argument("--skill-name", default="")
    parser.add_argument("--auto-refresh", action="store_true")
    args = parser.parse_args()

    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.input).read_text())

    html_content = generate_html(data, skill_name=args.skill_name, auto_refresh=args.auto_refresh)
    Path(args.output).write_text(html_content)
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
