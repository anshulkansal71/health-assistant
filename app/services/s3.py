import uuid
from functools import lru_cache

import boto3

from app.config import settings


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def upload_prescription(image_bytes: bytes, content_type: str, filename: str) -> str:
    key = f"prescriptions/{uuid.uuid4()}-{filename}"
    _client().put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=image_bytes,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return key


def delete_prescription(key: str) -> None:
    _client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)


def generate_presigned_url(key: str, expires_in: int) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
