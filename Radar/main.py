"""Entry point for the simulation radar."""

from __future__ import annotations

import argparse
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulation radar that tracks the mouse cursor.")
    parser.add_argument(
        "--size",
        type=int,
        default=213,
        help="radar window size in pixels (default: 213, one third of the original 640)",
    )
    parser.add_argument(
        "--rpm",
        type=float,
        default=12.0,
        help="sweep speed in revolutions per minute (default: 12, i.e. one turn per 5 seconds)",
    )
    parser.add_argument("--smoke-test", action="store_true", help="run a short self-test and exit (used by build checks)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.size < 120 or args.size > 2000:
        print("--size must be between 120 and 2000", file=sys.stderr)
        return 2
    if args.rpm <= 0:
        print("--rpm must be positive", file=sys.stderr)
        return 2
    from radar.app import run
    return run(size=args.size, rpm=args.rpm, smoke_test=args.smoke_test)


if __name__ == "__main__":
    raise SystemExit(main())
