"""Normalise posts obtained from authorised social/news APIs into review signals.

This module intentionally does not scrape websites or infer a person's location.
Only provider-supplied coordinates are retained; author identifiers are hashed.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Any

ALLOWED_PROVIDERS={"x","instagram","facebook","youtube","news_rss"}

TERMS={
 "construction":("illegal construction","new construction","building","structure","కట్టడం","నిర్మాణం"),
 "land_filling":("land filling","soil dumping","soil fill","earth filling","మట్టి","పూడ్చి"),
 "vegetation_clearance":("tree cutting","trees removed","vegetation cleared","చెట్లు"),
 "water_pollution":("water pollution","sewage","effluent","మురుగు"),
 "nala_blockage":("nala blocked","drain blocked","feeder channel","కాలువ"),
 "lake_encroachment":("lake encroachment","ftl","buffer zone","lake boundary","చెరువు"),
}

def category_hints(text: str | None) -> list[str]:
    value=(text or "").casefold()
    return [category for category,terms in TERMS.items() if any(term in value for term in terms)]

def normalize_post(provider: str, record: dict[str,Any]) -> dict[str,Any]:
    provider=provider.lower()
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError("Unsupported social provider")
    post_id=str(record.get("id") or "").strip()
    if not post_id:
        raise ValueError("Provider post ID is required")
    created=record.get("created_at")
    if not created:
        raise ValueError("Provider creation timestamp is required")
    created_at=datetime.fromisoformat(str(created).replace("Z","+00:00"))
    text_value=str(record.get("text") or record.get("title") or "").strip()
    author=str(record.get("author_id") or "")
    author_hash=hashlib.sha256(author.encode()).hexdigest() if author else None
    lat=record.get("latitude"); lon=record.get("longitude")
    if (lat is None) != (lon is None):
        raise ValueError("Latitude and longitude must be supplied together")
    if lat is not None:
        lat=float(lat); lon=float(lon)
        if not (-90<=lat<=90 and -180<=lon<=180):
            raise ValueError("Provider coordinates are outside WGS84 bounds")
    canonical={"provider":provider,"post_id":post_id,"created_at":created_at.isoformat(),
        "text":text_value.casefold(),"latitude":lat,"longitude":lon}
    fingerprint=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"provider":provider,"provider_post_id":post_id,"created_at":created_at.isoformat(),
        "text":text_value,"author_ref":author_hash,"url":record.get("url"),
        "latitude":lat,"longitude":lon,"fingerprint":fingerprint,
        "category_hints":category_hints(text_value),"trust":"UNVERIFIED",
        "source_metadata":record.get("source_metadata") or {}}
