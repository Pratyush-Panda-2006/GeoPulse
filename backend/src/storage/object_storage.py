import hashlib
import os

import boto3
from botocore.config import Config


BUCKET_NAME = "geopulse-sar"


def get_storage_client():
    connect_timeout = int(os.environ.get("OBJECT_STORAGE_CONNECT_TIMEOUT_SEC", 10))
    read_timeout = int(os.environ.get("OBJECT_STORAGE_READ_TIMEOUT_SEC", 60))
    config = Config(connect_timeout=connect_timeout, read_timeout=read_timeout)
    
    return boto3.client(
        "s3",
        endpoint_url=os.environ["AWS_ENDPOINT_URL_S3"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.environ["AWS_REGION"],
        config=config,
    )


def upload_bytes(
    content: bytes,
    object_key: str,
    content_type: str = "application/octet-stream",
) -> dict:
    client = get_storage_client()

    client.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=content,
        ContentType=content_type,
    )

    return {
        "storage_key": object_key,
        "file_size_bytes": len(content),
        "checksum_sha256": hashlib.sha256(content).hexdigest(),
    }


def download_bytes(object_key: str) -> bytes:
    """
    Download an object from Object Storage and return its raw bytes.
    """
    client = get_storage_client()

    response = client.get_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
    )

    return response["Body"].read()