# JSON Schemas for skill-creator

All files described here are produced or consumed by scripts in `scripts/skill-creator/`.

---

## SKILL.md (frontmatter)

```yaml
---
name: my-skill-name          # kebab-case, ≤64 chars, no consecutive hyphens
description: >               # ≤1024 chars, no angle brackets
  Trigger description. Written so Claude recognises when to invoke this skill.
  Include example user phrases and contextual cues.
license: MIT                 # optional
allowed-tools:               # optional list
  - Bash
  - Read
compatibility: ">=1.0.0"     # optional, max 500 chars
---
```

---

## evals.json

Test cases for trigger evaluation and output grading.

```json
{
  "skill": "my-skill-name",
  "cases": [
    {
      "id": "basic-trigger",
      "prompt": "User message that should trigger the skill",
      "description": "What a correct output looks like",
      "input_files": {
        "relative/path.txt": "file content"
      },
      "expectations": [
        "Output contains a summary section",
        "No hallucinated file paths"
      ],
      "should_trigger": true
    },
    {
      "id": "no-trigger",
      "prompt": "Message that should NOT trigger the skill",
      "should_trigger": false
    }
  ]
}
```

---

## grading.json

Output from the grader agent for one eval run.

```json
{
  "results": [
    {
      "expectation_id": "basic-trigger/0",
      "expectation": "Output contains a summary section",
      "verdict": "PASS",
      "evidence": "Line 14: '## Summary'"
    }
  ],
  "pass_rate": 0.85,
  "verified_claims": [
    { "claim": "...", "verdict": "VERIFIED", "evidence": "..." }
  ],
  "eval_suggestions": [],
  "timing": { "executor_seconds": 12.4, "grader_seconds": 3.1 }
}
```

---

## metrics.json

Executor performance data for one run.

```json
{
  "tool_calls": { "Read": 3, "Bash": 5, "Write": 2 },
  "total_steps": 10,
  "files_created": 2,
  "errors": 0,
  "output_chars": 4200,
  "transcript_chars": 18000
}
```

---

## timing.json

Wall-clock and token usage for one run.

```json
{
  "executor_start": "2026-06-07T10:00:00Z",
  "executor_end":   "2026-06-07T10:00:12Z",
  "grader_start":   "2026-06-07T10:00:12Z",
  "grader_end":     "2026-06-07T10:00:15Z",
  "total_tokens": 8400,
  "duration_ms": 15200
}
```

---

## benchmark.json

Aggregated results across multiple runs (with_skill vs without_skill).

```json
{
  "skill": "my-skill-name",
  "configs": {
    "with_skill": {
      "runs": 5,
      "pass_rate": { "mean": 0.82, "std": 0.04, "min": 0.75, "max": 0.88 },
      "time_seconds": { "mean": 14.2, "std": 1.1, "min": 12.8, "max": 16.0 },
      "tokens": { "mean": 8200, "std": 300, "min": 7800, "max": 8700 }
    },
    "without_skill": {
      "runs": 5,
      "pass_rate": { "mean": 0.55, "std": 0.07, "min": 0.44, "max": 0.66 },
      "time_seconds": { "mean": 11.0, "std": 0.9, "min": 9.8, "max": 12.3 },
      "tokens": { "mean": 6100, "std": 250, "min": 5800, "max": 6500 }
    }
  },
  "deltas": {
    "pass_rate": 0.27,
    "time_seconds": 3.2,
    "tokens": 2100
  }
}
```

---

## history.json

Iteration history for the improve loop.

```json
{
  "started": "2026-06-07T10:00:00Z",
  "skill": "my-skill-name",
  "best_version": 3,
  "iterations": [
    {
      "version": 1,
      "description": "Original description text",
      "train_pass_rate": 0.60,
      "test_pass_rate": 0.55,
      "parent": null
    },
    {
      "version": 2,
      "description": "Improved description text",
      "train_pass_rate": 0.80,
      "test_pass_rate": 0.75,
      "parent": 1
    }
  ]
}
```

---

## comparison.json

Blind comparator output.

```json
{
  "winner": "A",
  "reasoning": "A produced a more complete output with correct citations.",
  "scores": {
    "A": { "content": 8.0, "structure": 7.5, "overall": 7.75 },
    "B": { "content": 6.0, "structure": 6.5, "overall": 6.25 }
  },
  "rubric": {
    "content": [{ "criterion": "Correctness", "score_A": 4, "score_B": 3 }],
    "structure": [{ "criterion": "Formatting", "score_A": 4, "score_B": 3 }]
  },
  "quality_summary": {
    "A": { "strengths": ["..."], "weaknesses": ["..."] },
    "B": { "strengths": ["..."], "weaknesses": ["..."] }
  },
  "expectation_pass_rates": { "A": 0.9, "B": 0.6 }
}
```

---

## analysis.json

Post-hoc analyzer output.

```json
{
  "comparison_summary": "...",
  "winner": "A",
  "instruction_following_scores": { "A": 8, "B": 5 },
  "weaknesses": [
    {
      "skill": "B",
      "issue": "Missing step 3 in instructions",
      "evidence": "Transcript shows no lint step executed",
      "impact": "high"
    }
  ],
  "suggestions": [
    {
      "type": "instructions",
      "priority": "high",
      "description": "Add explicit lint step after file creation"
    }
  ]
}
```
