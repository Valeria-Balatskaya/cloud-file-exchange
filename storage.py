"""AWS S3 storage backend for cloud file exchange."""
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from flask import redirect

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception


log = logging.getLogger(__name__)


@dataclass
class StorageResult:
    key: str


class S3Storage:
    def __init__(
        self,
        bucket_name: str,
        region_name: str,
        access_key: Optional[str],
        secret_key: Optional[str],
        session_token: Optional[str],
        endpoint_url: Optional[str],
        presigned_ttl: int,
    ) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for S3 storage but is not installed")
        
        from botocore.config import Config as BotoConfig
        
        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token or None,
            region_name=region_name,
        )
        
        # Use s3v4 signature for all regions (required for eu-north-1 and other newer regions)
        boto_config = BotoConfig(
            signature_version='s3v4',
            s3={'addressing_style': 'virtual'}
        )
        
        # Use regional endpoint for proper presigned URL generation
        if not endpoint_url:
            endpoint_url = f'https://s3.{region_name}.amazonaws.com'
        
        self.client = session.client(
            "s3", 
            endpoint_url=endpoint_url,
            config=boto_config
        )
        self.bucket_name = bucket_name
        self.presigned_ttl = presigned_ttl
        self.region_name = region_name
        log.info("Using AWS S3 bucket '%s' in region '%s' for storage", bucket_name, region_name)
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except (BotoCoreError, ClientError) as exc:
            log.error("Cannot access S3 bucket %s", bucket_name, exc_info=exc)
            raise RuntimeError(
                "Cannot access configured S3 bucket. Check credentials, region, and bucket existence."
            ) from exc

    def save(self, file_storage, filename: str, user_id: int) -> StorageResult:
        object_key = f"user-{user_id}/{filename}"
        
        # Handle both regular file streams and BytesIO
        stream = file_storage.stream
        try:
            stream.seek(0)
        except (ValueError, IOError):
            # Stream might be closed, try to get content directly
            pass
        
        extra_args = {}
        if hasattr(file_storage, 'mimetype') and file_storage.mimetype:
            extra_args["ContentType"] = file_storage.mimetype
        try:
            self.client.upload_fileobj(
                stream,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args or None,
            )
        except (BotoCoreError, ClientError) as exc:
            log.error("Failed to upload file to S3", exc_info=exc)
            raise RuntimeError("Failed to upload file to S3") from exc
        return StorageResult(key=object_key)

    def delete(self, key: str) -> None:
        if not key:
            return
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
        except (BotoCoreError, ClientError) as exc:
            log.error("Failed to delete S3 object %s", key, exc_info=exc)
            raise RuntimeError("Failed to delete file from cloud storage") from exc

    def download(self, file_record):
        safe_name = quote(file_record.original_filename)
        disposition = f"attachment; filename*=UTF-8''{safe_name}"
        params = {
            "Bucket": self.bucket_name,
            "Key": file_record.file_path,
            "ResponseContentDisposition": disposition,
        }
        try:
            presigned_url = self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=self.presigned_ttl,
            )
        except (BotoCoreError, ClientError) as exc:
            log.error("Failed to create presigned URL for %s", file_record.file_path, exc_info=exc)
            raise RuntimeError("Cannot generate download URL") from exc
        return redirect(presigned_url)

    def get_file_content(self, file_record) -> Optional[bytes]:
        """Get raw file content from S3 for ZIP packaging."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=file_record.file_path
            )
            return response['Body'].read()
        except (BotoCoreError, ClientError) as exc:
            log.error("Failed to get S3 object content %s", file_record.file_path, exc_info=exc)
            return None


def get_storage_backend(config) -> S3Storage:
    """Initialize AWS S3 storage backend."""
    bucket_name = config.get("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME is required for AWS S3 storage")
    
    return S3Storage(
        bucket_name=bucket_name,
        region_name=config.get("S3_REGION", "eu-north-1"),
        access_key=config.get("AWS_ACCESS_KEY_ID"),
        secret_key=config.get("AWS_SECRET_ACCESS_KEY"),
        session_token=config.get("AWS_SESSION_TOKEN"),
        endpoint_url=config.get("S3_ENDPOINT_URL"),
        presigned_ttl=config.get("S3_PRESIGNED_TTL", 900),
    )
