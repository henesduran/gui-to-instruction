#!/usr/bin/env python3
"""
Convert pipeline JSON output to a Playwright test spec.

Usage:
    python adapter.py output.json
    python adapter.py output.json --test-name "Homepage flow" --output test.spec.js
    python adapter.py output.json --output -          # print to stdout
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Matches: "Enter {value} as the {field}." or "Enter {value} as {field}."
# Also handles optional context prefix: "Within the context of X, enter ..."
ENTRY_RE = re.compile(
    r"^(?:Within the context of .+?, )?[Ee]nter (.+?) as (?:the )?(.+?)\.$"
)

# Matches: "Click on {element}."
# Also handles optional context prefix: "Within the context of X, click on ..."
CLICK_RE = re.compile(
    r"^(?:Within the context of .+?, )?[Cc]lick on (.+?)\.$"
)


def _natural_key(k: str) -> int:
    digits = re.sub(r"[^0-9]", "", k)
    return int(digits) if digits else 0


def _make_step(key: str, item: dict) -> str:
    instruction = item.get("instruction", "")
    intent = item.get("intent", "click")
    compiled = item.get("compiled_instruction")

    lines: list[str] = []

    if compiled:
        lines.append(f"  // {key} — {intent} | compiled: {compiled}")
    else:
        lines.append(f"  // {key} — {intent}")

    if intent == "entry":
        m = ENTRY_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse entry instruction: {instruction!r}")
            return "\n".join(lines)
        value, field = m.group(1), m.group(2)
        lines.append(f"  await page.getByLabel('{field}').fill('{value}');")

    elif intent == "selectFromDropDown":
        m = CLICK_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse selectFromDropDown instruction: {instruction!r}")
            return "\n".join(lines)
        lines.append(f"  await page.getByRole('option', {{ name: '{m.group(1)}' }}).click();")

    elif intent == "selectDay":
        m = CLICK_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse selectDay instruction: {instruction!r}")
            return "\n".join(lines)
        lines.append(f"  await page.getByRole('gridcell', {{ name: '{m.group(1)}' }}).click();")

    elif intent == "increaseMonth":
        m = CLICK_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse increaseMonth instruction: {instruction!r}")
            return "\n".join(lines)
        lines.append(f"  await page.getByRole('button', {{ name: '{m.group(1)}' }}).click();")

    elif intent == "expandDropDown":
        m = CLICK_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse expandDropDown instruction: {instruction!r}")
            return "\n".join(lines)
        lines.append(f"  await page.getByRole('button', {{ name: '{m.group(1)}' }}).click();")

    else:  # click, openDatePicker
        m = CLICK_RE.match(instruction)
        if not m:
            lines.append(f"  // WARN: could not parse click instruction: {instruction!r}")
            return "\n".join(lines)
        lines.append(f"  await page.getByText('{m.group(1)}').click();")

    return "\n".join(lines)


def convert(input_path: str, test_name: str) -> str:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    steps = [
        _make_step(key, data[key])
        for key in sorted(data.keys(), key=_natural_key)
    ]
    body = "\n\n".join(steps)
    return (
        "const { test, expect } = require('@playwright/test');\n\n"
        f"test('{test_name}', async ({{ page }}) => {{\n"
        f"{body}\n"
        "});\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert pipeline JSON output to a Playwright .spec.js file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Pipeline JSON output file (e.g. output.json)")
    parser.add_argument(
        "--test-name",
        default="Generated test",
        help="Name of the Playwright test function.",
    )
    parser.add_argument(
        "--output",
        default="test.spec.js",
        help="Output file path. Use - to print to stdout.",
    )
    args = parser.parse_args()

    spec = convert(args.input, args.test_name)

    if args.output == "-":
        sys.stdout.write(spec)
    else:
        Path(args.output).write_text(spec, encoding="utf-8")
        print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
