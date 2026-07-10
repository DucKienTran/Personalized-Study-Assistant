import logging

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.config import settings
from app.core.dependencies import AuthServiceDep
from app.core.security import set_refresh_cookie
from app.exceptions import InvalidAdminRegistrationKeyError
from app.schemas.token_schema import TokenResponse
from app.schemas.user_schema import UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_client(user_data: UserRegister, service: AuthServiceDep):
    return service.register(user_data, role_name="client")


@router.post(
    "/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_admin(
    user_data: UserRegister,
    admin_key: str,
    service: AuthServiceDep,
):
    if admin_key != settings.ADMIN_REGISTRATION_KEY:
        logger.warning(
            f"Đăng ký admin thất bại: Mã xác thực Admin không hợp lệ (email={user_data.email})"
        )
        raise InvalidAdminRegistrationKeyError()
    return service.register(user_data, role_name="admin")


@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response,
    request: Request,
    form_data: UserLogin,
    service: AuthServiceDep,
):
    result = await service.login(form_data, request)
    set_refresh_cookie(response, result.pop("refresh_token"))
    return result


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: Request,
    service: AuthServiceDep,
    refresh_token: str = Cookie(None),
):
    result = await service.refresh(refresh_token, request)
    set_refresh_cookie(response, result.pop("refresh_token"))
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
