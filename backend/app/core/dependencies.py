from collections.abc import AsyncGenerator, Generator
from functools import lru_cache
import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.ai.llm.base import LLMClient
from app.ai.llm.gemini_client import GeminiClient
from app.core.database import SessionLocal, mongo_client, redis_client
from app.core.security import decode_token
from app.exceptions import (
    InternalServerError,
    MissingUserIdentityError,
    PermissionDeniedError,
)
from app.schemas.user_schema import CurrentUser
from app.services.ai.summary_service import SummaryService
from app.services.auth_service import AuthService
from app.services.document.document_service import DocumentService
from app.services.document.parser import DocumentParserService
from app.services.document.summary_record_service import SummaryRecordService
from app.services.presence_service import PresenceService
from app.services.user_service import UserService
from app.services.ai.quiz_service import QuizService

logger = logging.getLogger(__name__)
security = HTTPBearer()


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
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CurrentUser:
    """
    Dependency lấy thông tin người dùng từ Access Token
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

    def __call__(
        self,
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role == "admin":
            return current_user

        user_permissions = current_user.permissions or []
        if self.required_permission not in user_permissions:
            raise PermissionDeniedError(self.required_permission)

        return current_user


def get_presence_service(
    redis: Annotated[Redis, Depends(get_redis)],
) -> PresenceService:
    return PresenceService(redis)


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    presence: Annotated[PresenceService, Depends(get_presence_service)],
) -> AuthService:
    return AuthService(db, redis, presence)


def get_user_service(
    db: Annotated[Session, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    presence: Annotated[PresenceService, Depends(get_presence_service)],
) -> UserService:
    return UserService(db, redis, presence)


async def get_document_parser_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)],
) -> DocumentParserService:
    return DocumentParserService(mongo_db=db)


@lru_cache
def get_llm_client() -> LLMClient:
    """
    Khởi tạo singleton LLM client cho toàn bộ ứng dụng.
    """
    return GeminiClient()


def get_summary_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> SummaryService:
    return SummaryService(
        mongo_db=db,
        llm_client=llm_client,
    )


def get_document_service(
    db: Annotated[Session, Depends(get_db)],
    parser_service: Annotated[
        DocumentParserService, Depends(get_document_parser_service)
    ],
) -> DocumentService:
    return DocumentService(
        sql_db=db, mongo_db=mongo_client.db, parser_service=parser_service
    )


def get_summary_record_service(
    db: Annotated[Session, Depends(get_db)],
) -> SummaryRecordService:
    return SummaryRecordService(sql_db=db, mongo_db=mongo_client.db)


def get_quiz_service(
    db: Session = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
    llm_client: LLMClient = Depends(get_llm_client),
) -> QuizService:
    return QuizService(db, document_service, llm_client)


DbSession = Annotated[Session, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
PresenceServiceDep = Annotated[PresenceService, Depends(get_presence_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
DocumentParserServiceDep = Annotated[
    DocumentParserService, Depends(get_document_parser_service)
]
SummaryServiceDep = Annotated[
    SummaryService,
    Depends(get_summary_service),
]


SummaryRecordServiceDep = Annotated[
    SummaryRecordService,
    Depends(get_summary_record_service),
]

QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]
