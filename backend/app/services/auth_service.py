import logging

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    blacklist_refresh_token,
    is_refresh_token_blacklisted,
)
from app.models.user_model import User
from app.schemas.user_schema import UserLogin, UserRegister
from app.services.presence_service import PresenceService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session, redis: Redis, presence: PresenceService):
        self.db = db
        self.redis = redis
        self.presence = presence

    def register(self, user_data: UserRegister, role: str = "client") -> User:
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Đăng ký thất bại: Email {user_data.email} đã tồn tại")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký trên hệ thống.",
            )

        new_user = User(
            email=user_data.email,
            password=hash_password(user_data.password),
            role=role,
            full_name=user_data.full_name,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        logger.info(f"Đăng ký {role} thành công: [{new_user.id}, {user_data.email}, {role}]")
        return new_user

    async def login(self, form_data: UserLogin) -> dict:
        target_user = self.db.query(User).filter(User.email == form_data.email).first()

        if not target_user or not verify_password(form_data.password, target_user.password):
            logger.warning(f"Đăng nhập thất bại: Email {form_data.email} sai thông tin")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email hoặc mật khẩu không chính xác.",
            )

        if not target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa.",
            )

        token_payload = {"id": target_user.id, "sub": target_user.email, "role": target_user.role}
        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        await self.presence.mark_online(target_user.id)

        logger.info(
            f"Đăng nhập thành công: [{target_user.id}, {target_user.email}, {target_user.role}]"
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token: str) -> dict:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ (Missing Cookie).",
            )

        if await is_refresh_token_blacklisted(self.redis, refresh_token):
            logger.warning(f"Phát hiện hành vi tái sử dụng Refresh Token: {refresh_token}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên làm việc của bạn đã hết hạn hoặc thay đổi. Vui lòng đăng nhập lại.",
            )

        payload = decode_token(refresh_token, expected_type="refresh")
        user = self.db.query(User).filter(User.id == payload.get("id")).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản không tồn tại, đã bị xóa hoặc vô hiệu hóa.",
            )

        await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))

        new_payload = {"id": user.id, "sub": user.email, "role": user.role}
        new_refresh_token = create_refresh_token(new_payload)

        logger.info(f"Cấp lại token thành công: [{user.id}, {user.email}, {user.role}]")
        return {
            "access_token": create_access_token(new_payload),
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, refresh_token: str) -> dict:
        if refresh_token:
            payload = decode_token(refresh_token, expected_type="refresh", raise_on_error=False)
            if payload:
                await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))
                user_id = payload.get("id")
                await self.presence.clear_online_status(user_id)
                logger.info(f"Đăng xuất thành công: user_id={user_id}")

        return {"detail": "Đăng xuất thành công."}
