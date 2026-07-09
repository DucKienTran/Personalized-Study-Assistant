import logging
from typing import AsyncGenerator, Generator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.ai.summarizer import AISummarizerService
from app.core.config import settings
from app.core.mongodb import mongo_client
from app.core.mysql import SessionLocal
from app.core.redis import redis_client
from app.core.security import decode_token
from app.exceptions import (
    InternalServerError,
    MissingUserIdentityError,
    PermissionDeniedError,
)
from app.schemas.user_schema import CurrentUser
from app.services.auth_service import AuthService
from app.services.document.document_service import DocumentService
from app.services.document.parser import DocumentParserService
from app.services.document.summary_service import DocumentSummaryService
from app.services.presence_service import PresenceService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
security = HTTPBearer()

REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
ONLINE_STATUS_EXPIRE_SECONDS = settings.ONLINE_STATUS_EXPIRE_SECONDS


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_redis() -> AsyncGenerator[Redis, None]:
    try:
        yield redis_client
    finally:
        pass


async def get_mongodb():
    if mongo_client.db is None:
        raise InternalServerError(
            "MongoDB chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return mongo_client.db


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Dependency lấy thông tin người dùng từ Access Token theo cơ chế STATELESS.
    """
    token = credentials.credentials
    payload = decode_token(token, expected_type="access", raise_on_error=True)

    user_id = payload.get("id")
    email = payload.get("sub")
    role_name = payload.get("role")
    permissions = payload.get("permissions", [])

    if not user_id or not email:
        raise MissingUserIdentityError()

    return CurrentUser(id=user_id, email=email, role=role_name, permissions=permissions)


class PermissionChecker:
    """
    Dependency kiểm tra quyền hạn của User (RBAC)
    """

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        # Nếu là admin, tự động cho qua tất cả các quyền
        if current_user.role == "admin":
            return current_user

        # Kiến tra xem quyền yêu cầu có nằm trong danh sách quyền của User không
        user_permissions = current_user.permissions or []
        if self.required_permission not in user_permissions:
            raise PermissionDeniedError(self.required_permission)

        return current_user


# Lấy các Bussiness logic từ Services
def get_presence_service(
    redis: Redis = Depends(get_redis),
) -> PresenceService:
    return PresenceService(redis)


def get_auth_service(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    presence: PresenceService = Depends(get_presence_service),
) -> AuthService:
    return AuthService(db, redis, presence)


def get_user_service(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    presence: PresenceService = Depends(get_presence_service),
) -> UserService:
    return UserService(db, redis, presence)



async def get_document_parser_service(db=Depends(get_mongodb)) -> DocumentParserService:
    return DocumentParserService(mongo_db=db)


async def get_ai_summarizer_service(db=Depends(get_mongodb)) -> AISummarizerService:
    return AISummarizerService(mongo_db=db)


def get_document_service(
    db: Session = Depends(get_db),
    parser_service: DocumentParserService = Depends(
        get_document_parser_service
    ), 
) -> DocumentService:
    return DocumentService(sql_db=db, mongo_db=mongo_client.db, parser_service=parser_service)


def get_document_summary_service(db: Session = Depends(get_db)) -> DocumentSummaryService:
    return DocumentSummaryService(sql_db=db, mongo_db=mongo_client.db)
