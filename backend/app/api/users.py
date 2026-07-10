import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from app.core.dependencies import CurrentUserDep, UserServiceDep, get_current_user
from app.core.security import set_refresh_cookie
from app.schemas.user_schema import ChangePassword, UserResponse, UserStatus

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: CurrentUserDep,
    service: UserServiceDep,
):
    logger.info(f"Truy cập thông tin cá nhân: {current_user.id}, {current_user.email}")
    return service.get_user_profile(current_user)


@router.get("/all", response_model=List[UserResponse])
def get_all_users(
    current_user: CurrentUserDep,
    service: UserServiceDep,
):
    return service.get_all_users(current_user)


@router.get(
    "/get-status",
    status_code=status.HTTP_200_OK,
    response_model=Union[UserStatus, List[UserStatus]],
)
async def get_user_status(
    current_user: CurrentUserDep,
    service: UserServiceDep,
    target_id: Optional[int] = None,
):
    return await service.get_status(current_user, target_id)


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePassword,
    response: Response,
    request: Request,
    current_user: CurrentUserDep,
    service: UserServiceDep,
    refresh_token: str = Cookie(None),
):
    result = await service.change_password(current_user, data, refresh_token, request)
    set_refresh_cookie(response, result.pop("refresh_token"))
    return result


@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    response: Response,
    current_user: CurrentUserDep,
    service: UserServiceDep,
    target_id: Optional[int] = None,
    refresh_token: str = Cookie(None),
):
    result = await service.delete_account(current_user, target_id, refresh_token)

    if result.pop("self_deleted"):
        response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")

    return result
