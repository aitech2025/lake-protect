"""The notifier: follow-ups and the outbox, every minute (DECISIONS.md D-059).

    python -m app.notify run [--every 60]            # the notifier service (docker compose)
    python -m app.notify tick                        # once
    python -m app.notify digest [--week 2026-W48]
"""
from __future__ import annotations

import argparse
import json
import time

from app.clock import utcnow
from app.db import SessionLocal
from app.notify import service
from app.services import weeks as weeks_svc


def tick_once() -> dict:
    with SessionLocal() as db:
        out = service.tick(db, utcnow())
        db.commit()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.notify")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--every", type=int, default=60)
    sub.add_parser("tick")
    dig = sub.add_parser("digest")
    dig.add_argument("--week")
    args = parser.parse_args()

    if args.cmd == "tick":
        print(json.dumps(tick_once()))
    elif args.cmd == "digest":
        with SessionLocal() as db:
            week = args.week or service.latest_week(db) or weeks_svc.iso_week(utcnow().date())
            out = service.send_digests(db, week, utcnow())
            out["deliveries"] = service.send_pending(db, utcnow())
            db.commit()
        print(json.dumps(out))
    else:
        print(f"notifier: follow-ups and outbox every {args.every} s", flush=True)
        while True:
            try:
                out = tick_once()
                if out["reminders"] or out["not_acknowledged"] or out["deliveries"]:
                    print(json.dumps(out), flush=True)
            except Exception as exc:  # keep running: the next tick tries again
                print(f"notifier error: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(max(5, args.every))


if __name__ == "__main__":
    main()
