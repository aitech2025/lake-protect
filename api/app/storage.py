"""File storage behind an S3-style interface (section 11).

LocalDiskStore keeps objects under LP_STORAGE_DIR, a Docker volume outside OneDrive. A MinIO or
State object store can replace it by implementing the same four methods.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.config import settings


class ObjectStore(Protocol):
    def put_object(self, key: str, data: bytes) -> str: ...
    def get_object(self, key: str) -> bytes: ...
    def head_object(self, key: str) -> dict | None: ...
    def local_path(self, key: str) -> Path: ...


class LocalDiskStore:
    def __init__(self, root: Path, archive_root: Path | None = None):
        self.root = Path(root)
        self.archive_root = Path(archive_root) if archive_root is not None else self.root / "archive"

    def _path(self, key: str) -> Path:
        clean = PurePosixPath(key)
        if clean.is_absolute() or ".." in clean.parts:
            raise ValueError(f"Bad object key: {key}")
        if clean.parts and clean.parts[0] == "archive":
            if len(clean.parts) == 1:
                raise ValueError(f"Bad archive object key: {key}")
            return self.archive_root.joinpath(*clean.parts[1:])
        return self.root.joinpath(*clean.parts)

    def put_object(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return key

    def get_object(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def head_object(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        data = path.read_bytes()
        return {"key": key, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def local_path(self, key: str) -> Path:
        return self._path(key)


store: ObjectStore = LocalDiskStore(settings.storage_dir, settings.archive_dir)
