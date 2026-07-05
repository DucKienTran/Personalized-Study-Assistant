import logging
import time
from typing import AsyncGenerator, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mysql import SessionLocal
from app.core.redis import redis_client
from app.core.security import decode_token
from app.models.user_model import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.presence_service import PresenceService

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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_token(token, expected_type="access")

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning(
            f"Xác thực thất bại: Token hợp lệ nhưng không tìm thấy Email '{email}' trong Database."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại"
        )

    if not user.is_active:
        logger.warning(
            f"Truy cập bị chặn: Tài khoản [{user.id}, {user.email}] đang bị vô hiệu hóa."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa."
        )

    await redis_client.setex(f"user:status:{user.id}", ONLINE_STATUS_EXPIRE_SECONDS, "online")
    await redis_client.setex(
        f"user:last_active:{user.id}",
        REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        int(time.time()),
    )

    return user


# Lấy các Bussiness logic từ AuthService (register, login, refresh, logout v.v.) để sử dụng trong các route
def get_presence_service(redis: Redis = Depends(get_redis)) -> PresenceService:
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
