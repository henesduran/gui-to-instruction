#!/usr/bin/env python3
"""
CLI entry point for the GUI-to-instruction pipeline.

Usage:
    python run_tests.py --phase 1
    python run_tests.py --phase 1 --no-resume
    python run_tests.py --phase 3 --delay 10
"""

import argparse

from guiinstruct.pipeline import run

PHASE_CONFIG = {
    1: {"actions": "actions.json",    "screenshots": "examples",     "output": "output.json"},
    2: {"actions": "actions2.json",   "screenshots": "screenshots2", "output": "output2.json"},
    3: {"actions": "actions3.json",   "screenshots": "screenshots3", "output": "output5.json"},
    4: {"actions": "actions_ss.json", "screenshots": "screenshots",  "output": "output_ss.json"},
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the GUI-to-instruction pipeline on a phase dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="Dataset phase (1=click/entry, 2=dropdowns, 3=date pickers, 4=ss screenshots).",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Re-process all actions, ignoring any existing output file.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=15.0,
        help="Seconds between Gemini API calls.",
    )
    args = parser.parse_args()

    cfg = PHASE_CONFIG[args.phase]
    prompt_phase = 3 if args.phase == 4 else args.phase
    run(
        actions_path=cfg["actions"],
        screenshots_dir=cfg["screenshots"],
        output_path=cfg["output"],
        phase=prompt_phase,
        resume=not args.no_resume,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
