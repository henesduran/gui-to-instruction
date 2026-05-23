"""
Evaluation and statistics for pipeline outputs.

Metrics computed:
- Intent distribution (counts + percentages)
- Context disambiguation rate  (instructions containing "Within the context of")
- Compiled instruction coverage (phase 3)
- Average instruction length
"""

import json
import os
from collections import Counter


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _has_context(instruction: str) -> bool:
    return instruction.lower().startswith("within the context of")


def evaluate(output_path: str, phase: int | None = None) -> dict:
    """Return a metrics dict for a single output file."""
    data = _load_json(output_path)
    if not data:
        return {}

    instructions = [v.get("instruction", "") for v in data.values()]
    intents = [v.get("intent", "unknown") for v in data.values()]
    compiled = [v.get("compiled_instruction") for v in data.values()]

    n = len(data)
    intent_counts = dict(Counter(intents))
    context_count = sum(1 for i in instructions if _has_context(i))
    compiled_count = sum(1 for c in compiled if c)
    avg_len = sum(len(i) for i in instructions) / n if n else 0

    return {
        "total_samples": n,
        "intent_distribution": intent_counts,
        "context_disambiguation": {
            "count": context_count,
            "rate": round(context_count / n, 3) if n else 0,
        },
        "compiled_instructions": {
            "count": compiled_count,
            "rate": round(compiled_count / n, 3) if n else 0,
        },
        "avg_instruction_length_chars": round(avg_len, 1),
    }


def report(output_paths: dict[str, str]) -> None:
    """Print a formatted evaluation report for multiple output files.

    Args:
        output_paths: mapping of label → file path, e.g. {"Phase I": "output.json"}
    """
    print("=" * 60)
    print("  GUI-Instruct — Evaluation Report")
    print("=" * 60)

    all_intents: Counter = Counter()
    total_samples = 0

    for label, path in output_paths.items():
        if not os.path.exists(path):
            print(f"\n{label}: file not found ({path})")
            continue

        m = evaluate(path)
        n = m["total_samples"]
        total_samples += n
        all_intents.update(m["intent_distribution"])

        print(f"\n{label}  ({n} samples)")
        print("  Intent distribution:")
        for intent, count in sorted(m["intent_distribution"].items()):
            pct = count / n * 100
            print(f"    {intent:<22} {count:>3}  ({pct:.0f}%)")

        ctx = m["context_disambiguation"]
        print(f"  Context disambiguation:    {ctx['count']}/{n}  ({ctx['rate']*100:.0f}%)")

        comp = m["compiled_instructions"]
        if comp["count"] > 0:
            print(f"  Compiled instructions:     {comp['count']}/{n}  ({comp['rate']*100:.0f}%)")

        print(f"  Avg instruction length:    {m['avg_instruction_length_chars']} chars")

    print("\n" + "=" * 60)
    print(f"  Total samples:  {total_samples}")
    print("  Intent totals:")
    for intent, count in sorted(all_intents.items()):
        pct = count / total_samples * 100 if total_samples else 0
        print(f"    {intent:<22} {count:>3}  ({pct:.0f}%)")
    print("=" * 60)
