"""The WhatsApp conversation (CONTEXT.md 17.8; DECISIONS.md D-062).

One question at a time, by number or keyword, so it works on any phone and in any of the three
languages:
1. Language.
2. The place: a shared location pin, or a landmark in words.
3. What is happening, from five choices.
4. A photo, or SKIP.
5. A few words, or SKIP.
6. Updates on this number: YES or NO.

The report is then made like any other, and the reply gives the reference. Sending a reference at
any time returns its status; RESTART starts again.

**Where messages come from:**
- **Real messages** arrive at the webhook once the State has a WhatsApp Business agreement (its own
  number or MeeSeva on WhatsApp). Each is signed with the app secret, and unsigned messages are
  refused.
- **Until then**, the desk's simulator sends demo messages through the same conversation.

**Privacy.** The number is kept on the open chat only to reply, and removed after 24 hours without
a message. It stays on the report only if the citizen asked for updates.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.citizen import sender, service, texts
from app.models import CitizenChat, CitizenMessage

IDLE = dt.timedelta(hours=24)


def wa_hash(wa_id: str) -> str:
    return service.source_hash(f"wa:{wa_id}")


def signature_ok(raw_body: bytes, header: str | None) -> bool:
    secret = os.environ.get("LP_WHATSAPP_APP_SECRET")
    if not secret or not header or not header.startswith("sha256="):
        return False
    good = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.removeprefix("sha256="), good)


def _chat(db: Session, wa_id: str, is_demo: bool, at: dt.datetime) -> CitizenChat:
    h = wa_hash(wa_id)
    chat = db.scalar(select(CitizenChat).where(CitizenChat.wa_hash == h, CitizenChat.is_demo.is_(is_demo)))
    if chat is None:
        chat = CitizenChat(wa_hash=h, wa_id=wa_id, state="new", draft={}, is_demo=is_demo, updated_at=at)
        db.add(chat)
        db.flush()
    chat.wa_id = wa_id
    return chat


def _log(db: Session, chat: CitizenChat, direction: str, body: str, at: dt.datetime, *, status: str = "received",
         detail: str | None = None) -> CitizenMessage:
    lang = chat.language or "en"
    msg = CitizenMessage(report_id=chat.report_id, chat_id=chat.id, direction=direction, channel="whatsapp",
                         kind="chat_in" if direction == "in" else "chat_reply", language=lang, to_masked=sender.mask(f"+{chat.wa_id}"),
                         text=body, status=status, attempt=0 if direction == "in" else 1, detail=detail, is_demo=chat.is_demo, at=at)
    db.add(msg)
    db.flush()
    return msg


def _what_menu(lang: str) -> str:
    lines = [texts.pick(texts.BOT["ask_what"], lang)]
    lines += [f"{i} {texts.pick(texts.WHAT[w], lang)}" for i, w in enumerate(texts.WHAT_ORDER, start=1)]
    return "\n".join(lines)


def _question(chat: CitizenChat) -> str:
    lang = chat.language or "en"
    return {
        "lang": texts.BOT["welcome"],
        "place": texts.pick(texts.BOT["ask_place"], lang),
        "what": _what_menu(lang),
        "photo": texts.pick(texts.BOT["ask_photo"], lang),
        "describe": texts.pick(texts.BOT["ask_describe"], lang),
        "updates": texts.pick(texts.BOT["ask_updates"], lang),
    }.get(chat.state, texts.BOT["welcome"])


def _status_reply(db: Session, ref: str, lang: str) -> str:
    view = service.public_view(db, ref)
    if view is None:
        return texts.pick(texts.BOT["not_found"], lang)
    last = view["events"][-1]["note"] if view["events"] else {}
    return texts.pick(texts.BOT["status"], lang).format(ref=view["ref"], status=texts.pick(view["status_label"], lang),
                                                         note=texts.pick(last, lang))


def handle(db: Session, wa_id: str, message: dict, *, is_demo: bool, at: dt.datetime) -> list[str]:
    """One incoming message; returns the replies, which are also logged and sent (or held)."""
    chat = _chat(db, wa_id, is_demo, at)
    kind = message.get("type")
    body = (message.get("text") or "").strip()
    _log(db, chat, "in", body if kind == "text" else f"[{kind}]", at)
    replies = _step(db, chat, wa_id, kind, body, message, at)
    chat.updated_at = at
    for r in replies:
        result = sender.send_whatsapp(f"+{wa_id}", r, in_session=True, template_name=None, params=[], language=chat.language or "en",
                                      is_demo=chat.is_demo)
        _log(db, chat, "out", r, at, status=result.status, detail=result.detail)
    return replies


def _step(db: Session, chat: CitizenChat, wa_id: str, kind: str | None, body: str, message: dict, at: dt.datetime) -> list[str]:
    lang = chat.language or "en"
    word = body.lower()
    found = service.REF_RE.search(body.upper()) if kind == "text" else None
    if found:
        return [_status_reply(db, found.group(0), lang)]
    if word in ("restart", "menu", "start") or chat.state in ("new", "done"):
        chat.state, chat.draft, chat.report_id = "lang", {}, None
        return [texts.BOT["welcome"]]
    invalid = [f"{texts.pick(texts.BOT['invalid'], lang)}\n{_question(chat)}\n{texts.pick(texts.BOT['restart'], lang)}"]

    if chat.state == "lang":
        choice = {"1": "en", "2": "te", "3": "ur", "english": "en", "తెలుగు": "te", "اردو": "ur"}.get(word)
        if not choice:
            return [texts.BOT["welcome"]]
        chat.language, chat.state = choice, "place"
        return [_question(chat)]

    draft = dict(chat.draft or {})
    if chat.state == "place":
        if kind == "location":
            lon, lat = float(message["longitude"]), float(message["latitude"])
            if service.dataset_of(lon, lat) is not chat.is_demo:
                return [texts.pick(texts.BOT["outside"], lang)]
            draft.update(lon=lon, lat=lat)
        elif kind == "text" and len(body) >= 3:
            draft.update(location_text=body[:300])
        else:
            return invalid
        chat.draft, chat.state = draft, "what"
        return [_question(chat)]

    if chat.state == "what":
        try:
            what = texts.WHAT_ORDER[int(word) - 1]
        except (ValueError, IndexError):
            return invalid
        draft["what"] = what
        chat.draft, chat.state = draft, "photo"
        return [_question(chat)]

    if chat.state == "photo":
        if kind == "image":
            data = message.get("data")
            note = "photo_kept"
            if data:
                try:
                    photo = service.store_photo(f"chat-{chat.id}", len(draft.get("photos", [])) + 1, data)
                except service.CitizenError:
                    return invalid
                draft.setdefault("photos", []).append(photo)
            else:
                draft["photo_pending"] = True
                note = "photo_not_fetched"
            chat.draft, chat.state = draft, "describe"
            return [texts.pick(texts.BOT[note], lang), _question(chat)]
        if word in texts.SKIP:
            chat.state = "describe"
            return [_question(chat)]
        return invalid

    if chat.state == "describe":
        if kind != "text" or not body:
            return invalid
        if word not in texts.SKIP:
            draft["description"] = body[:1000]
        chat.draft, chat.state = draft, "updates"
        return [_question(chat)]

    if chat.state == "updates":
        if word in texts.YES:
            wants = True
        elif word in texts.NO:
            wants = False
        else:
            return invalid
        description = draft.get("description")
        if draft.get("photo_pending"):
            description = ((description or "") + " [A photo was sent on WhatsApp but could not be downloaded.]").strip()
        try:
            report = service.submit(
                db, channel="whatsapp", language=lang, what=draft["what"], at=at, source=wa_hash(wa_id),
                lon=draft.get("lon"), lat=draft.get("lat"), location_text=draft.get("location_text"), description=description,
                stored_photos=draft.get("photos", []), phone=f"+{wa_id}" if wants else None,
                phone_verified_via="whatsapp" if wants else None, wants_updates=wants, is_demo=chat.is_demo,
            )
        except service.TooMany:
            chat.state, chat.draft = "done", {}
            return [texts.pick(texts.BOT["too_many"], lang)]
        except service.CitizenError:
            chat.state, chat.draft = "done", {}
            return invalid
        chat.state, chat.draft, chat.report_id = "done", {}, report.id
        view = service.public_view(db, report.ref)
        first = " ".join(texts.pick(e["note"], lang) for e in view["events"])
        return [texts.pick(texts.BOT["done"], lang).format(first=first, ref=report.ref)]
    return invalid


def close_idle(db: Session, now: dt.datetime) -> int:
    """Chats with no message for 24 hours drop the number and start again next time."""
    chats = list(db.scalars(select(CitizenChat).where(CitizenChat.wa_id.is_not(None), CitizenChat.updated_at < now - IDLE)))
    for c in chats:
        c.wa_id, c.state, c.draft = None, "new", {}
    return len(chats)


def parse_webhook(body: dict) -> list[tuple[str, dict]]:
    """Messages from a WhatsApp Cloud API webhook: (sender's number, message)."""
    out = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            for m in (change.get("value") or {}).get("messages", []) or []:
                t = m.get("type")
                msg: dict = {"type": t}
                if t == "text":
                    msg["text"] = (m.get("text") or {}).get("body", "")
                elif t == "location":
                    msg.update(latitude=m["location"]["latitude"], longitude=m["location"]["longitude"])
                elif t == "image":
                    msg["media_id"] = (m.get("image") or {}).get("id")
                elif t == "interactive":
                    reply = (m.get("interactive") or {}).get("button_reply") or (m.get("interactive") or {}).get("list_reply") or {}
                    msg = {"type": "text", "text": reply.get("id") or reply.get("title") or ""}
                if m.get("from"):
                    out.append((str(m["from"]), msg))
    return out
