"""S3-compatible object storage upload for durable video URLs."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any


class UploadError(RuntimeError):
    pass


def _s3_configured() -> bool:
    return bool(
        os.environ.get("S3_BUCKET")
        and (
            os.environ.get("S3_ACCESS_KEY_ID")
            or os.environ.get("AWS_ACCESS_KEY_ID")
        )
        and (
            os.environ.get("S3_SECRET_ACCESS_KEY")
            or os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
    )


def upload_video(local_path: str | Path, *, prefix: str = "h3") -> dict[str, Any]:
    """Upload video and return URL metadata.

    If S3 is not configured, copies into OUTPUT_DIR and returns a file:// URL
    (useful for local / test_input.json runs).
    """
    path = Path(local_path)
    if not path.is_file():
        raise UploadError(f"Video file not found: {path}")

    key = f"{prefix.rstrip('/')}/{uuid.uuid4().hex}_{path.name}"

    if not _s3_configured():
        out_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp/h3_outputs"))
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / Path(key).name
        dest.write_bytes(path.read_bytes())
        return {
            "video_url": dest.as_uri(),
            "storage": "local",
            "key": str(dest),
        }

    import boto3
    from botocore.client import Config

    endpoint = os.environ.get("S3_ENDPOINT_URL") or None
    region = os.environ.get("S3_REGION", "auto")
    bucket = os.environ["S3_BUCKET"]
    access = os.environ.get("S3_ACCESS_KEY_ID") or os.environ["AWS_ACCESS_KEY_ID"]
    secret = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ["AWS_SECRET_ACCESS_KEY"]
    public_base = os.environ.get("S3_PUBLIC_BASE_URL", "").rstrip("/")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )

    extra: dict[str, Any] = {"ContentType": "video/mp4"}
    acl = os.environ.get("S3_ACL")
    if acl:
        extra["ACL"] = acl

    client.upload_file(str(path), bucket, key, ExtraArgs=extra)

    if public_base:
        url = f"{public_base}/{key}"
    else:
        expires = int(os.environ.get("S3_PRESIGN_SECONDS", "604800"))
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )

    return {"video_url": url, "storage": "s3", "bucket": bucket, "key": key}
