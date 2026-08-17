from abc import ABC, abstractmethod
from datetime import timedelta


class StorageService(ABC):
    """
    Abstract storage interface.

    Allows switching between
    - MinIO
    - AWS S3
    - Azure Blob
    - Local Storage
    """

    @abstractmethod
    async def upload_file(
        self,
        object_name: str,
        file_bytes: bytes,
        content_type: str,
    ) -> str:
        """
        Upload a file.

        Returns
        -------
        str
            Object name.
        """
        raise NotImplementedError

    @abstractmethod
    async def download_temp_file(
        self,
        object_name: str,
    ) -> str:
        """
        Download object to a temporary local file.

        Returns
        -------
        str
            Local temporary file path.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_file(
        self,
        object_name: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(minutes=15),
        response_headers: dict[str, str] | None = None,
    ) -> str:
        """
        Generate a short-lived, publicly-accessible URL for an object.

        Returns
        -------
        str
            Presigned URL.
        """
        raise NotImplementedError
