#!/usr/bin/env python3
"""
query.py — Ask a question against the wiki.

Usage:
    python scripts/wiki/query.py "What is attention mechanism?"
    python scripts/wiki/query.py "What is attention mechanism?" --file-answer

What it does:
1. Collects all wiki pages as context.
2. Prints a structured prompt for the LLM to answer from the wiki,
   with citations, and optionally file the answer back as a Q&A page.
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = REPO_ROOT / "wiki"


def slugify(text: str) -> str:
    text = text.lower().strip().rstrip("?")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60]


def collect_wiki(max_chars: int = 120_000) -> str:
    """Return concatenated wiki content, truncated to max_chars."""
    chunks = []
    total = 0
    for path in sorted(WIKI_DIR.rglob("*.md")):
        rel = path.relative_to(WIKI_DIR)
        header = f"\n\n--- wiki/{rel} ---\n"
        body = path.read_text(encoding="utf-8")
        chunk = header + body
        if total + len(chunk) > max_chars:
            chunks.append(f"\n\n[truncated — {path.name} and subsequent pages omitted]")
            break
        chunks.append(chunk)
        total += len(chunk)
    return "".join(chunks)


def build_prompt(question: str, file_answer: bool) -> str:
    today = datetime.date.today().isoformat()
    slug = slugify(question)
    qa_path = f"wiki/qa/{slug}.md"
    wiki_content = collect_wiki()

    file_instruction = f"""
5. FILE THE ANSWER as a new Q&A page at `{qa_path}` using this template
   (from wiki/schema.md):

   # Q: {question}

   **Asked**: {today}
   **Confidence**: <high | medium | low>

   ## Answer
   <your answer>

   ## Evidence
   - [[Page]] — supports because ...

   ## Caveats
   <anything uncertain or missing>

   ## Sources
   - <source files referenced>

   Then add a row to `wiki/index.md` under the Q&A section, and append to
   `wiki/log.md`:
   ## {today} HH:MM — query — {slug}
""".strip() if file_answer else "5. Do NOT create a new file. Print the answer only."

    return f"""
=== LLM QUERY TASK ===

Date: {today}
Question: {question}

Below is the full content of the wiki. Answer ONLY from what is stated or
directly implied by these pages. Do not use training-data knowledge unless
no relevant wiki page exists — in that case, say so explicitly and mark the
answer [low confidence].

{wiki_content}

Instructions:
1. IDENTIFY the most relevant wiki pages for this question.
2. SYNTHESIZE a clear, direct answer, citing pages with [[Page Name]].
3. NOTE contradictions or gaps in the wiki relevant to the question.
4. STATE a confidence tier (high / medium / low) with justification.
{file_instruction}
=== END TASK ===
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the LLM wiki.")
    parser.add_argument("question", help="The question to answer")
    parser.add_argument(
        "--file-answer",
        action="store_true",
        help="Instruct the LLM to file the answer as a Q&A page",
    )
    args = parser.parse_args()

    if not args.question.strip():
        sys.exit("[query] Question cannot be empty.")

    print(build_prompt(args.question, args.file_answer))


if __name__ == "__main__":
    main()
