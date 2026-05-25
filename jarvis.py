#!/usr/bin/env python3
"""Jarvis entry point."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make package importable when run from anywhere.
sys.path.insert(0, str(Path(__file__).parent))

from jarvis.core.config import load_config
from jarvis.core.assistant import Assistant


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis — personal AI assistant.")
    parser.add_argument("--config", help="Path to config.yaml (default: ~/.config/jarvis/config.yaml)")
    parser.add_argument("--headless", action="store_true", help="No GUI; CLI chat only")
    parser.add_argument("--say", help="One-shot: send this message, print reply, exit")
    parser.add_argument("--run-routine", help="One-shot: execute the named routine, then exit")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = load_config(args.config)
    assistant = Assistant(config)

    if args.say:
        reply = assistant.chat(args.say)
        print(reply)
        return 0

    if args.run_routine:
        assistant.run_routine_by_name(args.run_routine)
        return 0

    if args.headless:
        assistant.start_background_services()
        try:
            print("Jarvis (headless). Type 'quit' to exit.")
            while True:
                msg = input("> ").strip()
                if msg.lower() in {"quit", "exit"}:
                    break
                if not msg:
                    continue
                print(assistant.chat(msg))
        finally:
            assistant.shutdown()
        return 0

    from jarvis.gui.app import run_gui
    return run_gui(assistant)


if __name__ == "__main__":
    sys.exit(main())
