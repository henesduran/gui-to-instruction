#!/usr/bin/env python3
"""
CLI entry point for the GUI-to-instruction pipeline.

Usage:
    python run_tests.py --phase 1
    python run_tests.py --phase 1 --resume
    python run_tests.py --phase 3 --delay 10
"""

import argparse

from guiinstruct.pipeline import run

PHASE_CONFIG = {
    1: {"actions": "actions.json",  "screenshots": "examples",     "output": "output.json"},
    2: {"actions": "actions2.json", "screenshots": "screenshots2",  "output": "output2.json"},
    3: {"actions": "actions3.json", "screenshots": "screenshots3",  "output": "output5.json"},
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the GUI-to-instruction pipeline on a phase dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Dataset phase (1=click/entry, 2=dropdowns, 3=date pickers).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip actions already present in the output file.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="Seconds between Gemini API calls.",
    )
    args = parser.parse_args()

    cfg = PHASE_CONFIG[args.phase]
    run(
        actions_path=cfg["actions"],
        screenshots_dir=cfg["screenshots"],
        output_path=cfg["output"],
        phase=args.phase,
        resume=args.resume,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
