"""Scheduled workflow worker plus durable, retryable outbox delivery."""
from __future__ import annotations

import argparse
import logging
import os
import time
import uuid

import httpx
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal
from app.workflow import escalation

log = logging.getLogger("lake_protect.worker")


def retry_delay_seconds(attempt: int) -> int:
    """Bounded exponential retry: 30s, 60s ... capped at one hour."""
    return min(3600, 30 * (2 ** max(0, min(attempt - 1, 7))))


def _outbox_context(db) -> None:
    db.execute(text("""
      SELECT set_config('lp.outbox_worker','true',true),
             set_config('lp.is_platform_admin','false',true),
             set_config('lp.pipeline_ingest','false',true)
    """))


def _finish_outbox_event(event_id, worker_id: str, *, error: str | None = None,
                         published: bool = False, attempts: int = 1) -> bool:
    with SessionLocal() as db:
        _outbox_context(db)
        if published:
            result = db.execute(text("""
              UPDATE outbox_events
              SET published_at=now(), claimed_by=NULL, claimed_at=NULL,
                  next_attempt_at=NULL, last_error=NULL
              WHERE event_id=:event_id AND claimed_by=CAST(:worker_id AS uuid) AND published_at IS NULL
            """), {"event_id": event_id, "worker_id": worker_id})
        elif attempts >= settings.outbox_max_attempts:
            result = db.execute(text("""
              UPDATE outbox_events
              SET dead_lettered_at=now(), claimed_by=NULL, claimed_at=NULL,
                  next_attempt_at=NULL, last_error=:error
              WHERE event_id=:event_id AND claimed_by=CAST(:worker_id AS uuid) AND published_at IS NULL
            """), {"event_id": event_id, "worker_id": worker_id, "error": error})
        else:
            result = db.execute(text("""
              UPDATE outbox_events
              SET claimed_by=NULL, claimed_at=NULL,
                  next_attempt_at=now() + make_interval(secs => :delay),
                  last_error=:error
              WHERE event_id=:event_id AND claimed_by=CAST(:worker_id AS uuid) AND published_at IS NULL
            """), {"event_id": event_id, "worker_id": worker_id, "delay": retry_delay_seconds(attempts), "error": error})
        db.commit()
        return result.rowcount == 1


def publish_outbox_once() -> int:
    """Claim a batch in a short transaction; publish outside the transaction; finalize with lease ownership."""
    if not settings.outbox_webhook_url:
        return 0
    worker_id = str(uuid.uuid4())
    with SessionLocal() as db:
        _outbox_context(db)
        rows = db.execute(text("""
          WITH picked AS (
            SELECT id FROM outbox_events
            WHERE published_at IS NULL AND dead_lettered_at IS NULL
              AND (next_attempt_at IS NULL OR next_attempt_at <= now())
              AND (claimed_at IS NULL OR claimed_at < now() - make_interval(secs => :lease_seconds))
            ORDER BY occurred_at
            LIMIT :batch_size
            FOR UPDATE SKIP LOCKED
          )
          UPDATE outbox_events e
          SET claimed_by=CAST(:worker_id AS uuid), claimed_at=now(), publish_attempts=e.publish_attempts+1
          FROM picked p WHERE e.id=p.id
          RETURNING e.event_id,e.event_type,e.schema_version,e.aggregate_type,
                    e.aggregate_id,e.correlation_id,e.payload,e.publish_attempts,e.occurred_at
        """), {
            "lease_seconds": settings.outbox_claim_timeout_seconds,
            "batch_size": settings.outbox_batch_size,
            "worker_id": worker_id,
        }).mappings().all()
        db.commit()

    published = 0
    headers_base = {"Content-Type": "application/json"}
    if settings.outbox_webhook_token:
        headers_base["Authorization"] = f"Bearer {settings.outbox_webhook_token}"
    for event in rows:
        headers = {
            **headers_base,
            "Idempotency-Key": str(event["event_id"]),
            "X-Lake-Protect-Event": event["event_type"],
        }
        envelope = {
            "event_id": str(event["event_id"]),
            "event_type": event["event_type"],
            "schema_version": event["schema_version"],
            "aggregate_type": event["aggregate_type"],
            "aggregate_id": event["aggregate_id"],
            "correlation_id": str(event["correlation_id"]),
            "occurred_at": event["occurred_at"].isoformat(),
            "payload": event["payload"],
        }
        try:
            response = httpx.post(settings.outbox_webhook_url, json=envelope, headers=headers, timeout=httpx.Timeout(15.0, connect=3.0))
            response.raise_for_status()
            if _finish_outbox_event(event["event_id"], worker_id, published=True, attempts=event["publish_attempts"]):
                published += 1
        except (httpx.HTTPError, ValueError) as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            error = f"HTTP {status_code}" if status_code else type(exc).__name__
            _finish_outbox_event(event["event_id"], worker_id, error=error, attempts=event["publish_attempts"])
            log.warning("outbox delivery failed event_id=%s error=%s attempt=%s",
                        event["event_id"], error, event["publish_attempts"])
    return published


def tick() -> list[dict]:
    with SessionLocal() as db:
        misses = escalation.run(db)
        db.commit()
    sent = publish_outbox_once()
    log.info("outbox delivered: %d", sent)
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
        except Exception:
            log.exception("tick failed")
        if args.once:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
