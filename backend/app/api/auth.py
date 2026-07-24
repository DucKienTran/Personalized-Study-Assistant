import logging

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.config import settings
from app.core.dependencies import AuthServiceDep
from app.core.security import set_refresh_cookie
from app.exceptions import InvalidAdminRegistrationKeyError
from app.schemas.token_schema import TokenResponse
from app.schemas.user_schema import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    UserLogin,
    UserRegister,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/register", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def register_client(user_data: UserRegister, service: AuthServiceDep):
    return await service.register(user_data, role_name="client")


@router.post(
    "/register-admin", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def register_admin(
    user_data: UserRegister,
    admin_key: str,
    service: AuthServiceDep,
):
    if admin_key != settings.ADMIN_REGISTRATION_KEY:
        logger.warning(
            f"Admin registration failed: Invalid key for email={user_data.email}"
        )
        raise InvalidAdminRegistrationKeyError()
    return await service.register(user_data, role_name="admin")


@router.post(
    "/verify-email", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def verify_email(data: VerifyEmailRequest, service: AuthServiceDep):
    return await service.verify_email(data)


@router.post(
    "/forgot-password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def forgot_password(data: ForgotPasswordRequest, service: AuthServiceDep):
    return await service.forgot_password(data)


@router.post(
    "/reset-password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def reset_password(data: ResetPasswordRequest, service: AuthServiceDep):
    return await service.reset_password(data)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response,
    request: Request,
    form_data: UserLogin,
    service: AuthServiceDep,
):
    result = await service.login(form_data, request)
    set_refresh_cookie(
        response, result.pop("refresh_token"), remember_me=form_data.remember_me
    )
    return result


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: Request,
    service: AuthServiceDep,
    refresh_token: str = Cookie(None),
):
    result = await service.refresh(refresh_token, request)
    remember_me = result.pop("remember_me", False)
    set_refresh_cookie(
        response, result.pop("refresh_token"), remember_me=remember_me
    )
    return result


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    response: Response,
    service: AuthServiceDep,
    refresh_token: str = Cookie(None),
):
    result = await service.logout(refresh_token)
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")
    return result