#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.providers import GeminiProvider  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini CLI via SubAgent provider.")
    parser.add_argument("prompt", nargs="*", help="Prompt text (or stdin).")
    parser.add_argument("--model", default="gemini-2.0-pro")
    parser.add_argument("--live", action="store_true", help="Force live call.")
    args = parser.parse_args()

    prompt = " ".join(args.prompt) if args.prompt else sys.stdin.read()
    provider = GeminiProvider(model=args.model, allow_live=args.live)
    print(provider.generate(prompt))


if __name__ == "__main__":
    main()
