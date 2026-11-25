"""Command line for the asset creation engine.

    python -m app.sources list
    python -m app.sources run hmda_lpc --transport sample            # dry run: shows what would happen
    python -m app.sources run hmda_lpc --transport file_drop --apply  # loads an officer's drop
    python -m app.sources samples                                     # all four fictional samples, previewed in order

Runs from the command line have no user; the audit log records them as the system.
"""
from __future__ import annotations

import argparse
import json
import sys

from app.sources import engine
from app.sources.base import SourceError
from app.sources.connectors import CONNECTORS

SAMPLE_ORDER = ("hmda_lpc", "irrigation", "hydraa", "bhu_bharati")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.sources")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="each source and its data contract")
    run = sub.add_parser("run", help="run one source")
    run.add_argument("connector", choices=sorted(CONNECTORS))
    run.add_argument("--transport", choices=engine.TRANSPORTS, default="file_drop")
    run.add_argument("--apply", action="store_true", help="write the result; without it, a dry run")
    run.add_argument("--items", action="store_true", help="print every record, not just the counts")
    samples = sub.add_parser("samples", help="run all four fictional samples in order")
    samples.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "list":
        print(json.dumps([c.describe() for c in CONNECTORS.values()], indent=1, ensure_ascii=False))
        return 0

    from app.db import SessionLocal

    names = [args.connector] if args.cmd == "run" else list(SAMPLE_ORDER)
    transport = args.transport if args.cmd == "run" else "sample"
    if transport == "sample" and args.apply:
        # GeoGuard holds real data only (DECISIONS.md D-065): the fictional samples are previews.
        print("The sample registers are previews only: GeoGuard holds real data only", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        for name in names:
            try:
                report = engine.run(db, name, transport=transport, dry_run=not args.apply)
            except SourceError as exc:
                print(f"{name}: {exc}", file=sys.stderr)
                return 2
            shown = report if getattr(args, "items", False) else {k: v for k, v in report.items() if k != "items"}
            print(json.dumps(shown, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
