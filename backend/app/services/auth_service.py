from datetime import UTC, datetime
import logging

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.security import (
    blacklist_refresh_token,
    decode_token,
    generate_tokens_pair,
    hash_password,
    is_refresh_token_blacklisted,
    verify_password,
)
from app.models.user_model import RefreshToken, Role, User
from app.schemas.user_schema import UserLogin, UserRegister
from app.services.presence_service import PresenceService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session, redis: Redis, presence: PresenceService):
        self.db = db
        self.redis = redis
        self.presence = presence

    async def _revoke_all_user_tokens(self, user_id: int) -> None:
        await self.redis.setex(f"user:revoked:{user_id}", 86400 * 7, "true")
        await self.presence.clear_online_status(user_id)
        logger.critical(
            f"BẢO MẬT: Đã khóa khẩn cấp toàn bộ token hoạt động của User ID [{user_id}]"
        )

    def _save_refresh_token(
        self,
        user_id: int,
        refresh_token: str,
        jti: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )

        db_token = RefreshToken(
            user_id=user_id,
            jti=jti,
            revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
            expired_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )

        self.db.add(db_token)
        self.db.commit()

    def _revoke_refresh_token(self, jti: str) -> None:
        db_token = self.db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if db_token:
            db_token.revoked = True
            self.db.commit()

    def register(self, user_data: UserRegister, role_name: str = "client") -> User:
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Đăng ký thất bại: Email {user_data.email} đã tồn tại")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email này đã được đăng ký trên hệ thống.",
            )

        existing_username = self.db.query(User).filter(User.username == user_data.username).first()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên đăng nhập này đã tồn tại.",
            )
        db_role = self.db.query(Role).filter(Role.name == role_name).first()
        if not db_role:
            logger.error(
                f"Hệ thống cấu hình thiếu: Không tìm thấy nhóm quyền '{role_name}' trong DB bảng roles"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cấu hình hệ thống lỗi: Nhóm quyền '{role_name}' không tồn tại.",
            )

        new_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            role=db_role,
            full_name=user_data.full_name,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        logger.info(
            f"Đăng ký {role_name} thành công: [{new_user.id}, {user_data.email}, {db_role.name}]"
        )
        return new_user

    async def login(self, form_data: UserLogin, request: Request) -> dict:
        target_user = self.db.query(User).filter(User.email == form_data.email).first()

        if not target_user or not verify_password(form_data.password, target_user.password_hash):
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
        await self.redis.delete(f"user:revoked:{target_user.id}")

        tokens = generate_tokens_pair(
            user_id=target_user.id,
            email=target_user.email,
            role_name=target_user.role.name,
            permissions=[p.name for p in target_user.role.permissions],
        )

        self._save_refresh_token(
            user_id=target_user.id,
            refresh_token=tokens["refresh_token"],
            jti=tokens["jti"],
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )
        await self.presence.mark_online(target_user.id)

        logger.info(
            f"Người dùng [{target_user.id}, {target_user.email}] đăng nhập thành công. JTI: {tokens['jti']}"
        )
        return tokens

    async def refresh(self, refresh_token: str, request: Request) -> dict:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ (Missing Cookie).",
            )

        if await is_refresh_token_blacklisted(self.redis, refresh_token):
            try:
                payload = decode_token(refresh_token, expected_type="refresh", raise_on_error=False)
                if payload and payload.get("id"):
                    await self._revoke_all_user_tokens(payload.get("id"))
            except Exception as e:
                logger.error(f"Lỗi khi xử lý trích xuất info để revoke user: {str(e)}")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên bảo mật bị rò rỉ hoặc hết hạn. Vui lòng đăng nhập lại để đảm bảo an toàn.",
            )

        payload = decode_token(refresh_token, expected_type="refresh")
        db_token = self.db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()

        if not db_token:
            raise HTTPException(status_code=401, detail="Refresh token không tồn tại.")

        if db_token.revoked:
            raise HTTPException(status_code=401, detail="Refresh token đã bị thu hồi.")
        user_id = payload.get("id")

        if await self.redis.exists(f"user:revoked:{user_id}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phiên làm việc này đã bị hủy bỏ do nghi ngờ rò rỉ bảo mật. Vui lòng đăng nhập lại.",
            )

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tài khoản không tồn tại, đã bị xóa hoặc vô hiệu hóa.",
            )

        await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))
        self._revoke_refresh_token(payload.get("jti"))
        new_tokens = generate_tokens_pair(
            user_id=user.id,
            email=user.email,
            role_name=user.role.name,
            permissions=[p.name for p in user.role.permissions],
        )
        self._save_refresh_token(
            user_id=user.id,
            refresh_token=new_tokens["refresh_token"],
            jti=new_tokens["jti"],
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )
        await self.presence.mark_online(user.id)

        logger.info(
            f"Cấp lại token thành công cho user: [{user.id}, {user.email}]. JTI cũ: {payload.get('jti')} -> JTI mới: {new_tokens['jti']}"
        )
        return new_tokens

    async def logout(self, refresh_token: str) -> dict:
        if refresh_token:
            payload = decode_token(refresh_token, expected_type="refresh", raise_on_error=False)
            if payload:
                await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))
                user_id = payload.get("id")
                await self.presence.clear_online_status(user_id)
                self._revoke_refresh_token(payload.get("jti"))
                logger.info(f"Đăng xuất thành công: user_id={user_id}")

        return {"detail": "Đăng xuất thành công."}
