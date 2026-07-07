import logging
from typing import AsyncGenerator, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mysql import SessionLocal
from app.core.redis import redis_client
from app.core.security import decode_token
from app.schemas.user_schema import CurrentUser
from app.services.auth_service import AuthService
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ: Thiếu thông tin định danh người dùng",
        )

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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền thực hiện hành động này. Yêu cầu quyền: '{self.required_permission}'",
            )

        return current_user


# Lấy các Bussiness logic từ AuthService (register, login, refresh, logout v.v.) để sử dụng trong các route
def get_presence_service(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> PresenceService:
    return PresenceService(db, redis)


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
