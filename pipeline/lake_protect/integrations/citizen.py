"""Provider-neutral citizen report normalization and Meta webhook verification.

This module deliberately returns an untrusted report envelope. Callers must
persist it idempotently, malware-scan media, resolve jurisdiction and create an
incident through the existing workflow; a message is not a verified finding.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class CitizenReport:
    provider: str
    provider_message_id: str
    sender_ref: str
    received_at: str | None
    message_type: str
    text: str | None
    latitude: float | None
    longitude: float | None
    media_ids: tuple[str, ...]
    fingerprint: str
    trust: str = "UNVERIFIED"
    def as_dict(self) -> dict[str, Any]: return asdict(self)

def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Verify X-Hub-Signature-256; never accept an absent signature."""
    if not signature_header or not signature_header.startswith("sha256=") or not app_secret:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

def _fingerprint(sender: str, text: str | None, lat: float | None, lon: float | None, media: tuple[str,...]) -> str:
    canonical=json.dumps({"sender":sender,"text":(text or "").strip().casefold(),
        "lat":round(lat,5) if lat is not None else None,"lon":round(lon,5) if lon is not None else None,
        "media":sorted(media)},sort_keys=True,separators=(",",":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

def normalize_meta_webhook(payload: dict[str, Any]) -> list[CitizenReport]:
    """Extract inbound WhatsApp Cloud API messages, including location and media IDs."""
    reports=[]
    for entry in payload.get("entry",[]):
        for change in entry.get("changes",[]):
            value=change.get("value") or {}
            contacts={c.get("wa_id"):c for c in value.get("contacts",[])}
            for message in value.get("messages",[]):
                sender=str(message.get("from") or "")
                if not sender or not message.get("id"): continue
                kind=str(message.get("type") or "unknown")
                text_value=None; lat=lon=None; media=[]
                if kind=="text": text_value=(message.get("text") or {}).get("body")
                elif kind=="location":
                    location=message.get("location") or {}
                    try: lat=float(location["latitude"]); lon=float(location["longitude"])
                    except (KeyError,TypeError,ValueError): lat=lon=None
                    text_value=location.get("name") or location.get("address")
                elif kind in {"image","video","audio","document","sticker"}:
                    media_obj=message.get(kind) or {}
                    if media_obj.get("id"): media.append(str(media_obj["id"]))
                    text_value=media_obj.get("caption")
                media_ids=tuple(media)
                fp=_fingerprint(sender,text_value,lat,lon,media_ids)
                reports.append(CitizenReport(provider="whatsapp",provider_message_id=str(message["id"]),
                    sender_ref=hashlib.sha256(sender.encode()).hexdigest(),received_at=message.get("timestamp"),
                    message_type=kind,text=text_value,latitude=lat,longitude=lon,media_ids=media_ids,fingerprint=fp))
    return reports

CATEGORY_TERMS={
 "construction":("construction","building","house","structure","కట్టడం","నిర్మాణం"),
 "land_filling":("filling","soil","dumping","earth fill","మట్టి","పూడ్చి"),
 "vegetation_clearance":("tree cutting","trees removed","clearing","చెట్లు"),
 "water_pollution":("pollution","sewage","foam","మురుగు"),
 "nala_blockage":("blocked nala","drain blocked","channel blocked","కాలువ"),
}
def classify_report(text: str | None) -> list[str]:
    """Transparent multilingual keyword hints; never a legal classification."""
    value=(text or "").casefold()
    return [category for category,terms in CATEGORY_TERMS.items() if any(term in value for term in terms)]
