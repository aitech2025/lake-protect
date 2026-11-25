"""Messages to citizens by SMS and WhatsApp (DECISIONS.md D-062), on the terms of the officials' channels (D-059).

- **SMS** carries only the reference, the status and the link to the status page, because a DLT
  template fixes the words and allows 30 characters per value. The full note is on the portal.
- **WhatsApp**:
  - A reply inside an open conversation is plain text, allowed for 24 hours after the citizen's
    last message.
  - A later update needs an approved template.
- **Held until set up.** Both stay "held" until the State has a gateway agreement and registered or
  approved templates (channels.yaml).
- **Demo stays.** Demo messages never leave this machine; the WhatsApp simulator shows them.
- **Retries.** Every attempt is a new row. A failed attempt is retried after 5 minutes, up to three
  times.
"""
from __future__ import annotations

import datetime as dt
import os

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.citizen import texts
from app.config import settings
from app.models import CitizenChat, CitizenMessage, CitizenReport
from app.notify import channels
from app.notify.channels import DEMO_STAYS, Result

MAX_ATTEMPTS = 3
RETRY_AFTER = dt.timedelta(minutes=5)


def mask(phone: str | None) -> str | None:
    return channels.mask_phone(phone)


def track_link(ref: str) -> str:
    return settings.public_url.rstrip("/") + f"/report/track/{ref}"


def update_text(report: CitizenReport, status: str, note: dict) -> str:
    lang = report.language
    return f"GeoGuard {report.ref}: {texts.pick(texts.STATUS[status], lang)}. {texts.pick(note, lang)}\n{track_link(report.ref)}"


def queue_update(db: Session, report: CitizenReport, status: str, note: dict, at: dt.datetime) -> None:
    if not report.wants_updates or not report.reporter_phone:
        return
    channel = "whatsapp" if report.channel == "whatsapp" else "sms"
    db.add(CitizenMessage(report_id=report.id, direction="out", channel=channel, kind="update", language=report.language,
                          to_masked=mask(report.reporter_phone), text=update_text(report, status, note), status="queued",
                          attempt=0, is_demo=report.is_demo, at=at))


def sms_ready() -> bool:
    cfg = channels.config().get("sms") or {}
    return channels._not_ready("sms", cfg, (cfg.get("templates") or {}).get("citizen_update")) is None


def whatsapp_ready() -> bool:
    cfg = channels.config().get("whatsapp") or {}
    return bool(cfg.get("agreement_ref") and cfg.get("base_url"))


def _post(cfg: dict, body: dict, to: str | None) -> Result:
    import httpx

    token = os.environ.get(cfg.get("token_env") or "")
    if not token:
        return Result("held", f"The gateway credential {cfg.get('token_env')} is not set", to)
    try:
        resp = httpx.post(cfg["base_url"], json=body, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    except httpx.HTTPError as exc:
        return Result("failed", f"Gateway unreachable: {type(exc).__name__}", to)
    if resp.status_code >= 300:
        return Result("failed", f"Gateway answered {resp.status_code}", to)
    return Result("sent", "Accepted by the gateway", to)


def send_sms(phone: str, template_name: str, values: dict, is_demo: bool) -> Result:
    cfg = channels.config().get("sms") or {}
    template = (cfg.get("templates") or {}).get(template_name)
    to = mask(phone)
    reason = channels._not_ready("sms", cfg, template)
    if reason:
        return Result("held", reason, to)
    if is_demo:
        return Result("skipped", DEMO_STAYS, to)
    body = {"to": phone, "sender": cfg["sender_id"], "entity_id": cfg["dlt_entity_id"], "template_id": template["dlt_template_id"],
            "text": channels.render_dlt(template["text"], template["vars"], values)}
    return _post(cfg, body, to)


def send_whatsapp(phone: str, body_text: str, *, in_session: bool, template_name: str | None, params: list[str], language: str,
                  is_demo: bool) -> Result:
    cfg = channels.config().get("whatsapp") or {}
    to = mask(phone)
    template = (cfg.get("templates") or {}).get(template_name) if template_name else None
    if not cfg.get("agreement_ref") or not cfg.get("base_url"):
        return Result("held", "No WhatsApp agreement yet: the message waits here and is not sent", to)
    if not in_session and not (template or {}).get("approved"):
        return Result("held", "The WhatsApp template is not approved yet", to)
    if is_demo:
        return Result("skipped", DEMO_STAYS, to)
    if in_session:
        body = {"to": phone, "type": "text", "text": body_text}
    else:
        body = {"to": phone, "template": template["name"], "language": language, "params": params}
    return _post(cfg, body, to)


def _in_session(db: Session, msg: CitizenMessage) -> tuple[bool, CitizenChat | None]:
    chat = db.get(CitizenChat, msg.chat_id) if msg.chat_id else None
    if chat is None and msg.report_id:
        chat = db.scalar(select(CitizenChat).where(CitizenChat.report_id == msg.report_id).limit(1))
    open_ =chat is not None and chat.wa_id is not None and chat.updated_at >= msg.at - dt.timedelta(hours=24)
    return open_, chat


def attempt(db: Session, msg: CitizenMessage) -> Result:
    report = db.get(CitizenReport, msg.report_id) if msg.report_id else None
    if msg.channel == "sms":
        if report is None or not report.reporter_phone:
            return Result("skipped", "No phone number on file", msg.to_masked)
        values = {"ref": report.ref, "status": texts.STATUS[report.status]["en"], "link": track_link(report.ref)}
        return send_sms(report.reporter_phone, "citizen_update", values, msg.is_demo)
    in_session, chat = _in_session(db, msg)
    phone = (report.reporter_phone if report else None) or (f"+{chat.wa_id}" if chat and chat.wa_id else None)
    if not phone:
        return Result("skipped", "The conversation has closed and no number is kept", msg.to_masked)
    params = [report.ref, texts.STATUS[report.status]["en"], track_link(report.ref)] if report else []
    return send_whatsapp(phone, msg.text, in_session=in_session, template_name="citizen_update" if msg.kind == "update" else None,
                         params=params, language=msg.language, is_demo=msg.is_demo)


_PENDING = text(
    """
    SELECT m.id FROM citizen_messages m
    WHERE m.direction = 'out' AND m.status IN ('queued', 'failed') AND m.attempt < :max
      AND (m.status = 'queued' OR m.at <= :retry_before)
      AND NOT EXISTS (SELECT 1 FROM citizen_messages n WHERE n.retry_of = m.id)
    ORDER BY m.id LIMIT :n
    """
)


def record(db: Session, msg: CitizenMessage, result: Result, at: dt.datetime) -> CitizenMessage:
    row = CitizenMessage(report_id=msg.report_id, chat_id=msg.chat_id, direction="out", channel=msg.channel, kind=msg.kind,
                         language=msg.language, to_masked=result.to_masked or msg.to_masked, text=msg.text, status=result.status,
                         attempt=msg.attempt + 1, retry_of=msg.id, detail=result.detail, is_demo=msg.is_demo, at=at)
    db.add(row)
    db.flush()
    return row


def send_pending(db: Session, now: dt.datetime, limit: int = 200) -> dict:
    counts: dict[str, int] = {}
    for mid in db.scalars(_PENDING, {"max": MAX_ATTEMPTS, "retry_before": now - RETRY_AFTER, "n": limit}).all():
        msg = db.get(CitizenMessage, mid)
        result = attempt(db, msg)
        record(db, msg, result, now)
        counts[result.status] = counts.get(result.status, 0) + 1
    return counts


def status() -> dict:
    return {"sms_updates": sms_ready(), "whatsapp": whatsapp_ready()}
