"""The outside channels: email, SMS and WhatsApp (DECISIONS.md D-059).

Each channel turns one notification into one delivery attempt and says what happened:
- sent: the email was written or relayed, or the gateway accepted the message;
- held: the channel is not set up (no gateway agreement, registered template or approval yet);
- skipped: no address on file, or demo data on a channel that would leave this machine;
- failed: the relay or gateway refused; the outbox tries again, up to three attempts.

Demo notifications never leave the machine. Email in "file" mode is allowed for them, because it
only writes to the local outbox folder.
"""
from __future__ import annotations

import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from functools import lru_cache
from pathlib import Path

import yaml

from app.config import settings
from app.models import Notification, User
from app.storage import store

CONFIG_PATH = Path(__file__).with_name("channels.yaml")
DEMO_STAYS = "Demo data never leaves this machine"


@dataclass(frozen=True)
class Result:
    status: str
    detail: str
    to_masked: str | None = None


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return None
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    return value[:3] + "*" * max(len(value) - 7, 0) + value[-4:]


def carries(channel: str, kind: str) -> bool:
    return kind in (config().get(channel) or {}).get("kinds", [])


# Email ------------------------------------------------------------------------------------------
def email_message(note: Notification, user: User) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = user.email
    msg["Subject"] = ("[DEMO] " if note.is_demo else "") + note.subject
    msg["Date"] = format_datetime(note.created_at)
    msg["Message-ID"] = make_msgid(idstring=f"lp-notification-{note.id}", domain="lakeprotect.invalid")
    footer = "\n\n--\nLake Protect. Imagery shows physical change. It does not establish title or legality."
    if note.is_demo:
        footer += "\nDemo data: every place, name and incident in this message is fictional."
    msg.set_content(note.body + footer)
    return msg


def outbox_key(note: Notification, user: User) -> str:
    return f"outbox/email/{note.created_at:%Y-%m-%d}/{note.id:06d}-{re.sub(r'[^a-z0-9.]+', '-', user.username.lower())}.eml"


def send_email(note: Notification, user: User) -> Result:
    to = mask_email(user.email)
    transport = settings.email_transport
    if transport == "off":
        return Result("skipped", "Email is switched off (LP_EMAIL_TRANSPORT=off)", to)
    if transport == "file":
        key = store.put_object(outbox_key(note, user), bytes(email_message(note, user)))
        return Result("sent", f"Written to the local outbox: {key}", to)
    if transport != "smtp":
        return Result("held", f"Unknown email transport {transport!r}", to)
    if note.is_demo:
        return Result("skipped", DEMO_STAYS, to)
    if not settings.smtp_host:
        return Result("held", "No mail relay set (LP_SMTP_HOST)", to)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password or "")
            smtp.send_message(email_message(note, user))
    except (OSError, smtplib.SMTPException) as exc:
        return Result("failed", f"Mail relay refused: {type(exc).__name__}", to)
    return Result("sent", f"Relayed through {settings.smtp_host}", to)


# SMS and WhatsApp -------------------------------------------------------------------------------
def template_vars(note: Notification) -> dict:
    p = note.payload or {}
    return {
        "code": p.get("code", ""),
        "asset": p.get("asset_name", ""),
        "change_label": p.get("change_label", ""),
        "summary": p.get("summary", ""),
        "official": p.get("official_name", ""),
        "link": p.get("link", settings.public_url),
    }


def render_dlt(text: str, names: list[str], values: dict) -> str:
    """Fill a DLT template's {#var#} slots in order. Each value is cut to the 30 characters DLT allows."""
    parts = text.split("{#var#}")
    if len(parts) - 1 != len(names):
        raise ValueError("The template's {#var#} slots and its vars list differ")
    out = parts[0]
    for name, rest in zip(names, parts[1:]):
        out += str(values.get(name, ""))[:30] + rest
    return out


def _not_ready(channel: str, cfg: dict, template: dict | None) -> str | None:
    if not cfg.get("agreement_ref") or not cfg.get("base_url"):
        return f"No {channel_label(channel)} gateway agreement yet: the message waits here and is not sent"
    if channel == "sms" and (not cfg.get("dlt_entity_id") or not cfg.get("sender_id") or not (template or {}).get("dlt_template_id")):
        return "The DLT sender and template are not registered yet"
    if channel == "whatsapp" and not (template or {}).get("approved"):
        return "The WhatsApp template is not approved yet"
    return None


def channel_label(channel: str) -> str:
    return {"sms": "SMS", "whatsapp": "WhatsApp", "email": "email"}.get(channel, channel)


def send_template(channel: str, note: Notification, user: User) -> Result:
    import os

    import httpx

    cfg = config().get(channel) or {}
    template = (cfg.get("templates") or {}).get(note.kind)
    to = mask_phone(user.phone)
    reason = _not_ready(channel, cfg, template)
    if reason:
        return Result("held", reason, to)
    if note.is_demo:
        return Result("skipped", DEMO_STAYS, to)
    token = os.environ.get(cfg.get("token_env") or "")
    if not token:
        return Result("held", f"The gateway credential {cfg.get('token_env')} is not set", to)
    values = template_vars(note)
    if channel == "sms":
        body = {"to": user.phone, "sender": cfg["sender_id"], "entity_id": cfg["dlt_entity_id"],
                "template_id": template["dlt_template_id"], "text": render_dlt(template["text"], template["vars"], values)}
    else:
        body = {"to": user.phone, "template": template["name"], "language": "te" if user.language == "te" else "en",
                "params": [str(values.get(n, "")) for n in template["params"]]}
    try:
        resp = httpx.post(cfg["base_url"], json=body, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    except httpx.HTTPError as exc:
        return Result("failed", f"Gateway unreachable: {type(exc).__name__}", to)
    if resp.status_code >= 300:
        return Result("failed", f"Gateway answered {resp.status_code}", to)
    return Result("sent", f"Accepted by the {channel_label(channel)} gateway", to)


def send(channel: str, note: Notification, user: User) -> Result:
    if channel == "email":
        return send_email(note, user)
    if channel in ("sms", "whatsapp"):
        return send_template(channel, note, user)
    raise ValueError(f"Unknown channel {channel}")


def address(channel: str, user: User) -> str | None:
    return user.email if channel == "email" else user.phone


def status() -> list[dict]:
    """Is each channel ready to send? For the admin's page."""
    out = []
    transport = settings.email_transport
    email_ready = transport == "file" or (transport == "smtp" and bool(settings.smtp_host))
    email_detail = {
        "file": "Emails are written to the local outbox folder; nothing leaves this machine",
        "smtp": f"Emails go through the mail relay {settings.smtp_host}" if settings.smtp_host else "No mail relay set (LP_SMTP_HOST)",
        "off": "Email is switched off",
    }.get(transport, f"Unknown email transport {transport!r}")
    out.append({"channel": "email", "ready": email_ready, "mode": transport, "detail": email_detail})
    for channel in ("sms", "whatsapp"):
        cfg = config().get(channel) or {}
        reasons = {k: _not_ready(channel, cfg, t) for k, t in (cfg.get("templates") or {}).items()}
        first = next((r for r in reasons.values() if r), None)
        out.append({"channel": channel, "ready": first is None, "mode": "gateway" if first is None else "template",
                    "detail": first or f"Ready: {cfg.get('agreement_ref')}"})
    return out
