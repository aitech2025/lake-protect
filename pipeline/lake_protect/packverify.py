"""`lp verify-pack`: recompute every hash in an evidence pack (CONTEXT.md section 9.3).

Standard library only, so anyone can run it without the rest of the system. Written separately
from the code that builds packs, so the check does not share that code's assumptions.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(zip_path: str | Path, expected_manifest_sha256: str | None = None) -> dict:
    problems: list[str] = []
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "manifest_sha256": None, "files_checked": 0, "problems": [f"not a readable zip: {exc}"]}
    with z:
        names = set(z.namelist())
        if "manifest.json" not in names:
            return {"ok": False, "manifest_sha256": None, "files_checked": 0, "problems": ["manifest.json is missing"]}
        raw = z.read("manifest.json")
        manifest_sha = _sha256(raw)
        if expected_manifest_sha256 and manifest_sha != expected_manifest_sha256.lower():
            problems.append("manifest.json does not match the manifest hash recorded for this pack")
        try:
            manifest = json.loads(raw)
            listed = {f["path"]: f["sha256"] for f in manifest["files"]}
        except (ValueError, KeyError, TypeError) as exc:
            return {"ok": False, "manifest_sha256": manifest_sha, "files_checked": 0, "problems": [f"manifest.json is not valid: {exc}"]}
        for path, expected in sorted(listed.items()):
            if path not in names:
                problems.append(f"missing: {path}")
            elif _sha256(z.read(path)) != expected:
                problems.append(f"changed: {path}")
        for extra in sorted(names - set(listed) - {"manifest.json"}):
            problems.append(f"not listed in the manifest: {extra}")
    return {"ok": not problems, "manifest_sha256": manifest_sha, "files_checked": len(listed), "problems": problems}
