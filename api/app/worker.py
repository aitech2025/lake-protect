"""The scheduled worker (section 11: one scheduled worker container).

Each tick records missed timers and escalates them (section 6.6). The weekly re-check from space
needs the detection pipeline (M2 and M3), so it is not run here yet.

    python -m app.worker            # loop forever
    python -m app.worker --once     # one tick
"""
from __future__ import annotations

import argparse
import logging
import os
import time

from app.db import SessionLocal
from app.workflow import escalation

log = logging.getLogger("lake_protect.worker")


def tick() -> list[dict]:
    with SessionLocal() as db:
        misses = escalation.run(db)
        db.commit()
    for m in misses:
        log.info("timer missed: alert %s in %s, notify %s (level %s)", m["alert_id"], m["state"], m["notify"], m["escalation_level"])
    return misses


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    interval = int(os.environ.get("LP_WORKER_INTERVAL_SECONDS", "300"))
    while True:
        try:
            misses = tick()
            log.info("tick done: %d new missed timers", len(misses))
        except Exception:  # keep the worker alive; the next tick retries
            log.exception("tick failed")
        if args.once:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
