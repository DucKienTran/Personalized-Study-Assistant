import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Cookie, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_presence_service, get_redis
from app.api.v1.auth import _set_refresh_cookie
from app.models.user_model import User
from app.schemas.user_schema import ChangePassword, UserResponse, UserStatus
from app.services.presence_service import PresenceService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)


def get_user_service(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    presence: PresenceService = Depends(get_presence_service),
) -> UserService:
    return UserService(db, redis, presence)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    logger.info(f"Truy cập thông tin cá nhân: {current_user.id}, {current_user.email}")
    return current_user


@router.get("/all", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return service.get_all_users(current_user)


@router.get(
    "/get-status",
    status_code=status.HTTP_200_OK,
    response_model=Union[UserStatus, List[UserStatus]],
)
async def get_user_status(
    target_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.get_status(current_user, target_id)


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePassword,
    response: Response,
    current_user: User = Depends(get_current_user),
    refresh_token: str = Cookie(None),
    service: UserService = Depends(get_user_service),
):
    result = await service.change_password(current_user, data, refresh_token)
    _set_refresh_cookie(response, result.pop("refresh_token"))
    return result


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    response: Response,
    target_id: Optional[int] = None,
    refresh_token: str = Cookie(None),
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    result = await service.delete_account(current_user, target_id, refresh_token)

    if result.pop("self_deleted"):
        response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")

    return result
