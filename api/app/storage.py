"""Pluggable object storage for evidence and geospatial artifacts.

LocalDiskStore is for development. S3ObjectStore supports S3 and MinIO-compatible storage;
production bucket versioning, encryption, lifecycle, replication and access policies are configured
outside the application by infrastructure owners.
"""
from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.config import settings


class ObjectStore(Protocol):
    def put_object(self, key: str, data: bytes) -> str: ...
    def get_object(self, key: str) -> bytes: ...
    def head_object(self, key: str) -> dict | None: ...


def _safe_key(key: str) -> PurePosixPath:
    clean = PurePosixPath(key)
    if not key or clean.is_absolute() or ".." in clean.parts or "\x00" in key:
        raise ValueError(f"Bad object key: {key!r}")
    return clean


class LocalDiskStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        clean = _safe_key(key)
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

    def get_object_range(self, key: str, start: int, end: int) -> bytes:
        if start < 0 or end < start:
            raise ValueError("Invalid byte range")
        with self._path(key).open("rb") as stream:
            stream.seek(start)
            return stream.read(end - start + 1)

    def local_path(self, key: str) -> Path:
        return self._path(key)


class S3ObjectStore:
    def __init__(self, bucket: str, client, kms_key_id: str | None = None):
        if not bucket:
            raise ValueError("LP_S3_BUCKET is required when LP_STORAGE_BACKEND=s3")
        self.bucket = bucket
        self.client = client
        self.kms_key_id = kms_key_id

    def put_object(self, key: str, data: bytes) -> str:
        clean = str(_safe_key(key))
        digest = hashlib.sha256(data).hexdigest()
        content_type = mimetypes.guess_type(clean)[0] or "application/octet-stream"
        args = {
            "Bucket": self.bucket,
            "Key": clean,
            "Body": data,
            "ContentType": content_type,
            "Metadata": {"sha256": digest},
        }
        if self.kms_key_id:
            args["ServerSideEncryption"] = "aws:kms"
            args["SSEKMSKeyId"] = self.kms_key_id
        self.client.put_object(**args)
        return clean

    def get_object(self, key: str) -> bytes:
        clean = str(_safe_key(key))
        response = self.client.get_object(Bucket=self.bucket, Key=clean)
        return response["Body"].read()

    def get_object_range(self, key: str, start: int, end: int) -> bytes:
        if start < 0 or end < start:
            raise ValueError("Invalid byte range")
        clean = str(_safe_key(key))
        response = self.client.get_object(Bucket=self.bucket, Key=clean, Range=f"bytes={start}-{end}")
        return response["Body"].read()

    def head_object(self, key: str) -> dict | None:
        from botocore.exceptions import ClientError
        clean = str(_safe_key(key))
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=clean)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return {
            "key": clean,
            "size": response.get("ContentLength"),
            "sha256": response.get("Metadata", {}).get("sha256"),
            "etag": response.get("ETag"),
            "version_id": response.get("VersionId"),
            "last_modified": response.get("LastModified"),
        }

    def presigned_get_url(self, key: str, expires_seconds: int = 300) -> str:
        if not 1 <= expires_seconds <= 3600:
            raise ValueError("Presigned URL expiry must be between 1 and 3600 seconds")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": str(_safe_key(key))},
            ExpiresIn=expires_seconds,
        )


def create_store(config=settings) -> ObjectStore:
    if config.storage_backend == "local":
        return LocalDiskStore(config.storage_dir)
    if config.storage_backend != "s3":
        raise ValueError(f"Unsupported object storage backend: {config.storage_backend}")
    import boto3
    from botocore.config import Config
    client = boto3.client(
        "s3",
        endpoint_url=config.s3_endpoint_url,
        region_name=config.s3_region,
        aws_access_key_id=config.s3_access_key_id,
        aws_secret_access_key=config.s3_secret_access_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )
    return S3ObjectStore(config.s3_bucket, client, config.s3_kms_key_id)


store: ObjectStore = create_store()
