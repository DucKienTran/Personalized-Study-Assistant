from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse, urlunparse

from minio import Minio

from app.core.config import settings
from app.storage.base import StorageService


class MinIOStorageService(StorageService):
    """
    Storage implementation using MinIO.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False,
    ) -> None:

        self.bucket_name = bucket_name

        # Chỉ dùng internal endpoint để backend giao tiếp với MinIO
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    async def upload_file(
        self,
        object_name: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        from io import BytesIO

        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )

        return object_name

    async def download_temp_file(
        self,
        object_name: str,
    ) -> str:
        suffix = Path(object_name).suffix

        temp = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        )
        temp.close()

        self.client.fget_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=temp.name,
        )

        return temp.name

    async def delete_temp_file(
        self,
        temp_path: str,
    ) -> None:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    async def delete_file(
        self,
        object_name: str,
    ) -> None:
        self.client.remove_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
        )

    async def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(minutes=15),
    ) -> str:
        url = self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=expires,
        )

        parsed = urlparse(url)

        return urlunparse(parsed._replace(netloc="storage.learningaid.local:9000"))


class MinIOStorageManager:
    def __init__(self):
        self.service: MinIOStorageService | None = None

    def init_service(self):
        self.service = MinIOStorageService(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket_name=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )

    def close_service(self):
        # MinIO Python client không cần đóng kết nối thủ công.
        pass


minio_manager = MinIOStorageManager()
