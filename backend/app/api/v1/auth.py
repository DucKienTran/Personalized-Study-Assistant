import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from app.api.dependencies import get_auth_service
from app.core.config import settings
from app.schemas.token_schema import TokenResponse
from app.schemas.user_schema import UserLogin, UserRegister, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_client(user_data: UserRegister, service: AuthService = Depends(get_auth_service)):
    return service.register(user_data, role_name="client")


@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_admin(
    user_data: UserRegister,
    admin_key: str,
    service: AuthService = Depends(get_auth_service),
):
    if admin_key != settings.ADMIN_REGISTRATION_KEY:
        logger.warning(
            f"Đăng ký admin thất bại: Mã xác thực Admin không hợp lệ (email={user_data.email})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Mã xác thực Admin không hợp lệ."
        )
    return service.register(user_data, role_name="admin")


# Helper giúp set cookie refresh token trong response
def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response,
    request: Request,
    form_data: UserLogin,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.login(form_data, request)
    _set_refresh_cookie(response, result.pop("refresh_token"))
    return result


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: Request,
    refresh_token: str = Cookie(None),
    service: AuthService = Depends(get_auth_service),
):
    result = await service.refresh(refresh_token, request)
    _set_refresh_cookie(response, result.pop("refresh_token"))
    return result


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    response: Response,
    refresh_token: str = Cookie(None),
    service: AuthService = Depends(get_auth_service),
):
    result = await service.logout(refresh_token)
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")
    return result
