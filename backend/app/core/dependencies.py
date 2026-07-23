from collections.abc import AsyncGenerator, Generator
from functools import lru_cache
import logging
from typing import Annotated

from chromadb.api import ClientAPI
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from sqlalchemy.orm import Session

# --- LLM & EMBEDDING CLIENTS ---
from app.ai.embeddings.base import BaseEmbeddingClient
from app.ai.embeddings.voyage_client import VoyageEmbeddingClient
from app.ai.llm.base import LLMClient
from app.ai.llm.gemini_client import GeminiClient
from app.core.database import SessionLocal, chroma_client, mongo_client, redis_client
from app.core.security import decode_token
from app.exceptions import (
    InternalServerError,
    MissingUserIdentityError,
    PermissionDeniedError,
)
from app.schemas.user_schema import CurrentUser

# --- SERVICES ---
from app.services.ai.classifier_service import AIClassifier
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.quiz_service import QuizService
from app.services.ai.summary_service import SummaryService
from app.services.auth_service import AuthService
from app.services.document.document_processing_service import DocumentProcessingService
from app.services.document.document_service import DocumentService
from app.services.document.parser import DocumentParserService
from app.services.document.summary_record_service import SummaryRecordService
from app.services.presence_service import PresenceService
from app.services.user_service import UserService
from app.storage.base import StorageService
from app.storage.minio_storage import (
    minio_manager,  # thay cho MinIOStorageService
)
from app.services.ai.rag_service import RAGService
from app.services.ai.retrieval_service import RetrievalService

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


async def get_mongodb() -> AsyncIOMotorDatabase:
    if mongo_client.db is None:
        raise InternalServerError(
            "MongoDB chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return mongo_client.db


def get_chroma_client() -> ClientAPI:
    if chroma_client.client is None:
        raise InternalServerError(
            "ChromaDB chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return chroma_client.client


def get_storage_service() -> StorageService:
    if minio_manager.service is None:
        raise InternalServerError(
            "MinIO chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return minio_manager.service


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


async def get_document_parser_service() -> DocumentParserService:
    return DocumentParserService()


@lru_cache
def get_llm_client() -> LLMClient:
    """
    Khởi tạo singleton LLM client cho toàn bộ ứng dụng.
    """
    return GeminiClient()


@lru_cache
def get_embedding_client() -> BaseEmbeddingClient:
    """
    Khởi tạo singleton Embedding client (Voyage AI) cho toàn bộ ứng dụng.
    """
    return VoyageEmbeddingClient()


def get_embedding_service(
    embedding_client: Annotated[BaseEmbeddingClient, Depends(get_embedding_client)],
) -> EmbeddingService:
    """
    Khởi tạo EmbeddingService nhận client từ get_embedding_client.
    """
    return EmbeddingService(client=embedding_client)


def get_ai_classifier(
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> AIClassifier:
    """
    Khởi tạo bộ phân loại tài liệu sử dụng LLM Client
    """
    return AIClassifier(llm_client=llm_client)


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
    mongo_db: Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)],
    storage_service: Annotated[
        StorageService,
        Depends(get_storage_service),
    ],
) -> DocumentService:
    return DocumentService(
        sql_db=db,
        mongo_db=mongo_db,
        storage_service=storage_service,
    )


def get_document_processing_service(
    db: Annotated[Session, Depends(get_db)],
    mongo_db: Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)],
    chroma_client: Annotated[ClientAPI, Depends(get_chroma_client)],
    parser_service: Annotated[
        DocumentParserService,
        Depends(get_document_parser_service),
    ],
    storage_service: Annotated[
        StorageService,
        Depends(get_storage_service),
    ],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> DocumentProcessingService:
    return DocumentProcessingService(
        sql_db=db,
        mongo_db=mongo_db,
        chroma_client=chroma_client,
        parser_service=parser_service,
        storage_service=storage_service,
        llm_client=llm_client,
    )


def get_summary_record_service(
    db: Annotated[Session, Depends(get_db)],
    mongo_db: Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)],
) -> SummaryRecordService:
    return SummaryRecordService(sql_db=db, mongo_db=mongo_db)


def get_quiz_service(
    db: Annotated[Session, Depends(get_db)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> QuizService:
    return QuizService(db, document_service, llm_client)


def get_retrieval_service(
    chroma_client: Annotated[ClientAPI, Depends(get_chroma_client)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> RetrievalService:
    return RetrievalService(
        chroma_client=chroma_client,
        embedding_service=embedding_service,
    )


def get_rag_service(
    retrieval_service: Annotated[
        RetrievalService,
        Depends(get_retrieval_service),
    ],
    llm_client: Annotated[
        LLMClient,
        Depends(get_llm_client),
    ],
) -> RAGService:
    return RAGService(
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )


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
DocumentProcessingServiceDep = Annotated[
    DocumentProcessingService, Depends(get_document_processing_service)
]
AIClassifierDep = Annotated[AIClassifier, Depends(get_ai_classifier)]
EmbeddingClientDep = Annotated[BaseEmbeddingClient, Depends(get_embedding_client)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
SummaryServiceDep = Annotated[
    SummaryService,
    Depends(get_summary_service),
]
SummaryRecordServiceDep = Annotated[
    SummaryRecordService,
    Depends(get_summary_record_service),
]
QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]
ChromaClientDep = Annotated[ClientAPI, Depends(get_chroma_client)]

RetrievalServiceDep = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]

RAGServiceDep = Annotated[
    RAGService,
    Depends(get_rag_service),
]
