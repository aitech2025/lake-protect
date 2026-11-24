"""Remove personal fields from a file before it is stored or read (CONTEXT.md 17.10).

Detection and the register stay owner-blind. A Record of Rights extract may arrive with the
pattadar's name, a phone number or an Aadhaar number; those columns are dropped here, before the
file is stored, so they never reach the database or the object store. The snapshot records the
names of the columns that were dropped, never their values.
"""
from __future__ import annotations

import csv
import io
import json
import re

# Matched against a column or property name, lower-cased with spaces and dashes as underscores.
_PERSONAL = re.compile(
    r"pattadar|khatadar|owner|claimant|occupant|enjoyer|father|husband|guardian|relation"
    r"|aadhaar|aadhar|\buid\b|mobile|phone|e_?mail|address|person|applicant|^name_of"
)
# Names of places and assets, not people. Checked before the pattern above.
_ALLOWED = {
    "name", "name_te", "lake_name", "lake_name_te", "tank_name", "tank_name_te", "parcel_name",
    "village", "mandal", "district", "bhudhaar",
}


def _norm(column: str) -> str:
    return re.sub(r"[\s\-]+", "_", column.strip().lower())


def is_personal(column: str) -> bool:
    key = _norm(column)
    return key not in _ALLOWED and bool(_PERSONAL.search(key))


def sanitise(content: bytes, fmt: str) -> tuple[bytes, list[str]]:
    """The file without personal fields, and the sorted names of the fields removed."""
    if fmt == "csv":
        return _sanitise_csv(content)
    if fmt == "geojson":
        return _sanitise_geojson(content)
    raise ValueError(f"Unknown format {fmt}")


def _sanitise_csv(content: bytes) -> tuple[bytes, list[str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    dropped = sorted({c for c in columns if is_personal(c)})
    if not dropped:
        return content, []
    kept = [c for c in columns if c not in dropped]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=kept, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in reader:
        writer.writerow({k: row.get(k, "") for k in kept})
    return out.getvalue().encode("utf-8"), dropped


def _sanitise_geojson(content: bytes) -> tuple[bytes, list[str]]:
    try:
        doc = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return content, []  # not JSON: the connector reports the error when it reads the file
    dropped: set[str] = set()
    for feature in doc.get("features") or []:
        props = feature.get("properties") or {}
        for key in [k for k in props if is_personal(k)]:
            dropped.add(key)
            del props[key]
    if not dropped:
        return content, []
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), sorted(dropped)
