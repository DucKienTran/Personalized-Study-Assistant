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
from app.ai.llm.azure_openai_client import AzureOpenAIClient
from app.ai.llm.base import LLMClient

# --- INFRASTRUCTURE ---
from app.core.database import SessionLocal, chroma_client, mongo_client, redis_client
from app.core.security import decode_token
from app.exceptions import (
    InternalServerError,
    MissingUserIdentityError,
    PermissionDeniedError,
)
from app.exceptions.auth import InvalidTokenError
from app.schemas.user_schema import CurrentUser

# --- SERVICES ---
from app.services.ai.classifier_service import AIClassifier
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.quiz_service import QuizService
from app.services.ai.rag_service import RAGService
from app.services.ai.retrieval_service import RetrievalService
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService
from app.services.document.document_processing_service import DocumentProcessingService
from app.services.document.document_service import DocumentService
from app.services.document.parser import DocumentParserService
from app.services.email_service import EmailService
from app.services.notebook.notebook_service import NotebookService
from app.services.presence_service import PresenceService
from app.services.summary.summary_record_service import SummaryRecordService
from app.services.summary.summary_service import SummaryService
from app.services.user_service import UserService
from app.storage.base import StorageService
from app.storage.minio_storage import minio_manager

logger = logging.getLogger(__name__)
security = HTTPBearer()


# ==========================================
# 1. BASE / INFRASTRUCTURE DEPENDENCIES
# ==========================================


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


async def get_redis() -> AsyncGenerator[Redis, None]:
    try:
        yield redis_client
    finally:
        pass


RedisDep = Annotated[Redis, Depends(get_redis)]


async def get_mongodb() -> AsyncIOMotorDatabase:
    if mongo_client.db is None:
        raise InternalServerError(
            "MongoDB chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return mongo_client.db


MongoDbDep = Annotated[AsyncIOMotorDatabase, Depends(get_mongodb)]


def get_email_service() -> EmailService:
    return EmailService()


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


def get_chroma_client() -> ClientAPI:
    if chroma_client.client is None:
        raise InternalServerError(
            "ChromaDB chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return chroma_client.client


ChromaClientDep = Annotated[ClientAPI, Depends(get_chroma_client)]


def get_storage_service() -> StorageService:
    if minio_manager.service is None:
        raise InternalServerError(
            "MinIO chưa được khởi tạo! Vui lòng kiểm tra lại cấu hình lifespan trong main.py"
        )
    return minio_manager.service


StorageServiceDep = Annotated[StorageService, Depends(get_storage_service)]


@lru_cache
def get_llm_client() -> LLMClient:
    return AzureOpenAIClient()
    # return GeminiClient()


LLMClientDep = Annotated[LLMClient, Depends(get_llm_client)]


@lru_cache
def get_embedding_client() -> BaseEmbeddingClient:
    return VoyageEmbeddingClient()


EmbeddingClientDep = Annotated[BaseEmbeddingClient, Depends(get_embedding_client)]


# ==========================================
# 2. SECURITY & AUTH DEPENDENCIES
# ==========================================


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    redis: RedisDep,
) -> CurrentUser:
    token = credentials.credentials
    payload = decode_token(token, expected_type="access", raise_on_error=True)
    user_id = payload.get("id")
    email = payload.get("sub")
    role_name = payload.get("role")
    permissions = payload.get("permissions", [])

    if not user_id or not email:
        raise MissingUserIdentityError()

    revoked = await redis.exists(f"user:revoked:{user_id}")
    if revoked:
        raise InvalidTokenError("User session has been revoked.")

    return CurrentUser(
        id=user_id,
        email=email,
        role=role_name,
        permissions=permissions,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(
        self,
        current_user: CurrentUserDep,
    ) -> CurrentUser:
        if current_user.role == "admin":
            return current_user

        user_permissions = current_user.permissions or []
        if self.required_permission not in user_permissions:
            raise PermissionDeniedError(self.required_permission)

        return current_user


# ==========================================
# 3. SERVICE DEPENDENCIES
# ==========================================


def get_notebook_service(
    db: DbSession,
) -> NotebookService:
    return NotebookService(db=db)


NotebookServiceDep = Annotated[NotebookService, Depends(get_notebook_service)]


def get_presence_service(redis: RedisDep) -> PresenceService:
    return PresenceService(redis)


PresenceServiceDep = Annotated[PresenceService, Depends(get_presence_service)]


def get_auth_service(
    db: DbSession,
    redis: RedisDep,
    presence: PresenceServiceDep,
    email_service: EmailServiceDep,
) -> AuthService:
    return AuthService(db=db, redis=redis, presence=presence, email_service=email_service)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_user_service(
    db: DbSession,
    redis: RedisDep,
    presence: PresenceServiceDep,
) -> UserService:
    return UserService(db, redis, presence)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_document_parser_service() -> DocumentParserService:
    return DocumentParserService()


DocumentParserServiceDep = Annotated[DocumentParserService, Depends(get_document_parser_service)]


def get_embedding_service(
    embedding_client: EmbeddingClientDep,
) -> EmbeddingService:
    return EmbeddingService(client=embedding_client)


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


def get_ai_classifier(
    llm_client: LLMClientDep,
) -> AIClassifier:
    return AIClassifier(llm_client=llm_client)


AIClassifierDep = Annotated[AIClassifier, Depends(get_ai_classifier)]


def get_document_service(
    db: DbSession,
    mongo_db: MongoDbDep,
    storage_service: StorageServiceDep,
    chroma_client: ChromaClientDep,
    redis: RedisDep,
) -> DocumentService:
    return DocumentService(
        sql_db=db,
        mongo_db=mongo_db,
        storage_service=storage_service,
        chroma_client=chroma_client,
        redis=redis,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


def get_document_processing_service(
    db: DbSession,
    mongo_db: MongoDbDep,
    chroma_client: ChromaClientDep,
    parser_service: DocumentParserServiceDep,
    storage_service: StorageServiceDep,
    llm_client: LLMClientDep,
    redis: RedisDep,
) -> DocumentProcessingService:
    return DocumentProcessingService(
        sql_db=db,
        mongo_db=mongo_db,
        chroma_client=chroma_client,
        parser_service=parser_service,
        storage_service=storage_service,
        llm_client=llm_client,
        redis=redis,
    )


DocumentProcessingServiceDep = Annotated[
    DocumentProcessingService, Depends(get_document_processing_service)
]


def get_summary_service(
    db: DbSession,
    mongo_db: MongoDbDep,
    chroma_client: ChromaClientDep,
    llm_client: LLMClientDep,
) -> SummaryService:
    return SummaryService(
        sql_db=db,
        mongo_db=mongo_db,
        chroma_client=chroma_client,
        llm_client=llm_client,
    )


SummaryServiceDep = Annotated[
    SummaryService,
    Depends(get_summary_service),
]


def get_summary_record_service(
    db: DbSession,
    mongo_db: MongoDbDep,
) -> SummaryRecordService:
    return SummaryRecordService(sql_db=db, mongo_db=mongo_db)


SummaryRecordServiceDep = Annotated[
    SummaryRecordService, Depends(get_summary_record_service)
] 


def get_quiz_service(
    db: DbSession,
    document_service: DocumentServiceDep,
    llm_client: LLMClientDep,
) -> QuizService:
    return QuizService(db, document_service, llm_client)


QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]


def get_retrieval_service(
    chroma_client: ChromaClientDep,
    embedding_service: EmbeddingServiceDep,
    redis: RedisDep,
) -> RetrievalService:
    return RetrievalService(
        chroma_client=chroma_client,
        embedding_service=embedding_service,
        redis=redis,
    )


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


def get_rag_service(
    retrieval_service: RetrievalServiceDep,
    llm_client: LLMClientDep,
) -> RAGService:
    return RAGService(
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )


RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]


def get_conversation_service() -> ConversationService:
    return ConversationService()


ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
