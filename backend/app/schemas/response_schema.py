from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# Schema chuẩn để Router dùng định dạng đầu ra tự động
class BaseResponse(BaseModel, Generic[T]):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None
