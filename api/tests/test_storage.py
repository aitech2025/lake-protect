import io
from botocore.exceptions import ClientError
import pytest

from app.storage import LocalDiskStore, S3ObjectStore


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.last_put = None

    def put_object(self, **kwargs):
        self.last_put = kwargs
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = {
            "body": kwargs["Body"], "metadata": kwargs["Metadata"],
            "content_type": kwargs["ContentType"],
        }

    def get_object(self, Bucket, Key, **kwargs):
        item = self.objects[(Bucket, Key)]
        body = item["body"]
        if "Range" in kwargs:
            start, end = map(int, kwargs["Range"].removeprefix("bytes=").split("-"))
            body = body[start:end + 1]
        return {"Body": io.BytesIO(body)}

    def head_object(self, Bucket, Key):
        item = self.objects.get((Bucket, Key))
        if item is None:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "HeadObject")
        return {"ContentLength": len(item["body"]), "Metadata": item["metadata"], "ETag": '"etag-1"', "VersionId": "v1"}

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://objects.example/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"


def test_s3_put_get_head_and_integrity_metadata():
    client = FakeS3()
    store = S3ObjectStore("lake-protect", client, kms_key_id="kms-key")
    key = store.put_object("evidence/case-1/file.png", b"png-bytes")
    head = store.head_object(key)
    assert store.get_object(key) == b"png-bytes"
    assert head["size"] == 9
    assert head["sha256"] is not None
    assert client.last_put["ServerSideEncryption"] == "aws:kms"
    assert client.last_put["SSEKMSKeyId"] == "kms-key"


def test_s3_range_and_presigned_url():
    store = S3ObjectStore("bucket", FakeS3())
    store.put_object("rasters/tile.tif", b"0123456789")
    assert store.get_object_range("rasters/tile.tif", 2, 5) == b"2345"
    assert store.presigned_get_url("rasters/tile.tif", 60).endswith("expires=60")
    with pytest.raises(ValueError):
        store.presigned_get_url("rasters/tile.tif", 3601)


def test_s3_missing_object_returns_none_and_rejects_unsafe_keys():
    store = S3ObjectStore("bucket", FakeS3())
    assert store.head_object("missing.png") is None
    with pytest.raises(ValueError):
        store.get_object("../secret")


def test_local_disk_store_atomic_round_trip_and_range(tmp_path):
    store = LocalDiskStore(tmp_path)
    store.put_object("a/b.txt", b"012345")
    assert store.get_object("a/b.txt") == b"012345"
    assert store.get_object_range("a/b.txt", 1, 3) == b"123"
    assert store.head_object("a/b.txt")["size"] == 6
