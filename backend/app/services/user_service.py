from datetime import UTC, datetime
import logging
import time
from typing import List, Optional, Union

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    blacklist_refresh_token,
    decode_token,
    generate_tokens_pair,
    hash_password,
    is_refresh_token_blacklisted,
    verify_password,
)
from app.exceptions import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user_model import RefreshToken, User
from app.schemas.user_schema import ChangePassword, CurrentUser
from app.services.presence_service import PresenceService

logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
ONE_MINUTE, ONE_HOUR, ONE_DAY = 60, 3600, 86400


class UserService:
    def __init__(self, db: Session, redis: Redis, presence: PresenceService):
        self.db = db
        self.redis = redis
        self.presence = presence

    def get_user_profile(self, current_user: CurrentUser) -> User:
        user = self.db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise NotFoundError("Người dùng không tồn tại.")
        return user

    async def _revoke_all_user_tokens(self, user_id: int) -> None:
        await self.redis.setex(f"user:revoked:{user_id}", 86400 * 7, "true")
        await self.presence.clear_online_status(user_id)
        logger.info(
            f"Đã kích hoạt cờ thu hồi toàn bộ phiên làm việc của User ID [{user_id}]"
        )
        (
            self.db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .update(
                {"revoked": True},
                synchronize_session=False,
            )
        )
        self.db.commit()

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

    def get_all_users(self, current_user: CurrentUser) -> List[User]:
        if current_user.role != "admin":
            logger.warning(
                f"Truy cập trái phép: [{current_user.id}, {current_user.email}, {current_user.role}] "
                f"cố gắng truy cập danh sách users"
            )
            raise ForbiddenError(
                "Bạn không có quyền truy cập vào danh sách người dùng (Yêu cầu quyền Admin)."
            )

        logger.info(
            f"Truy cập danh sách người dùng thành công: ADMIN [{current_user.id}, {current_user.email}]"
        )
        return self.db.query(User).all()

    async def get_status(
        self, current_user: CurrentUser, target_id: Optional[int]
    ) -> Union[dict, List[dict]]:
        if current_user.role != "admin":
            logger.warning(
                f"Cảnh báo bảo mật: User [{current_user.id}] cố gắng xem trạng thái người dùng."
            )
            raise ForbiddenError(
                "Bạn không có quyền xem trạng thái của người dùng (Yêu cầu quyền Admin)."
            )

        # Xem cho 1 người
        if target_id:
            target_user = self.db.query(User).filter(User.id == target_id).first()
            if not target_user:
                raise NotFoundError("Không tìm thấy người dùng này.")
            return await self._format_user_status(target_user)

        # Xem tất cả mọi người
        all_users = self.db.query(User).all()
        return [await self._format_user_status(u) for u in all_users]

    # Helper function to format user status
    async def _format_user_status(self, target_user: User) -> dict:
        user_id = target_user.id
        presence_data = await self.presence.get_raw_presence(user_id)
        last_active_int = presence_data["last_active"]

        base = {
            "user_id": user_id,
            "email": target_user.email,
            "role": target_user.role.name,
            "last_active": last_active_int,
        }

        # Nếu đang online
        if presence_data["is_online"]:
            return {**base, "status": "online", "message": "Đang hoạt động"}

        # Nếu offline quá lâu hoặc chưa từng online
        if not last_active_int:
            return {**base, "status": "offline", "message": "Không hoạt động"}

        seconds_offline = int(time.time()) - last_active_int
        if seconds_offline < ONE_HOUR:
            message = f"Hoạt động {seconds_offline // ONE_MINUTE} phút trước"
        elif seconds_offline < ONE_DAY:
            message = f"Hoạt động {seconds_offline // ONE_HOUR} giờ trước"
        else:
            message = f"Hoạt động {seconds_offline // ONE_DAY} ngày trước"

        return {**base, "status": "offline", "message": message}

    async def change_password(
        self,
        current_user: CurrentUser,
        data: ChangePassword,
        refresh_token: Optional[str],
        request: Request,
    ) -> dict:
        db_user = self.db.query(User).filter(User.id == current_user.id).first()
        if not db_user:
            raise NotFoundError("Người dùng không tồn tại.")
        if not verify_password(data.old_password, db_user.password_hash):
            logger.warning(
                f"Đổi mật khẩu thất bại: [{current_user.id}] nhập sai mật khẩu cũ."
            )
            raise BadRequestError("Mật khẩu cũ không chính xác.")

        if verify_password(data.new_password, db_user.password_hash):
            logger.warning(
                f"Đổi mật khẩu thất bại: [{current_user.id}] mật khẩu mới trùng mật khẩu cũ."
            )
            raise BadRequestError("Mật khẩu mới không được trùng với mật khẩu cũ.")

        if not refresh_token:
            raise UnauthorizedError(
                "Phiên đăng nhập đã hết hạn hoặc không hợp lệ (Missing Cookie)."
            )

        if await is_refresh_token_blacklisted(self.redis, refresh_token):
            logger.warning(
                f"Phát hiện hành vi tái sử dụng Refresh Token: {refresh_token}"
            )
            raise UnauthorizedError(
                "Phiên làm việc của bạn đã hết hạn hoặc thay đổi. Vui lòng đăng nhập lại."
            )

        payload = decode_token(refresh_token, expected_type="refresh")
        if payload.get("id") != current_user.id:
            logger.error(
                f"CẢNH BÁO: Bất đồng bộ định danh! Access [{current_user.id}] với Refresh [{payload.get('id')}]."
            )
            raise BadRequestError("Thông tin xác thực không đồng nhất.")

        db_user.password_hash = hash_password(data.new_password)
        self.db.commit()
        logger.info(
            f"Đổi mật khẩu thành công: [{current_user.id}, {current_user.email}]"
        )

        await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))
        await self._revoke_all_user_tokens(db_user.id)
        await self.redis.delete(f"user:revoked:{db_user.id}")

        tokens = generate_tokens_pair(
            user_id=db_user.id,
            email=db_user.email,
            role_name=db_user.role.name,
            permissions=[p.name for p in db_user.role.permissions],
        )
        self._save_refresh_token(
            user_id=db_user.id,
            refresh_token=tokens["refresh_token"],
            jti=tokens["jti"],
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )

        await self.presence.mark_online(db_user.id)

        logger.info(
            f"Cấp lại token thành công sau đổi mật khẩu cho user: [{db_user.id}]"
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
            "detail": "Thay đổi mật khẩu thành công.",
        }

    async def delete_account(
        self, current_user: User, target_id: Optional[int], refresh_token: Optional[str]
    ) -> dict:
        is_self_deletion = (target_id is None) or (target_id == current_user.id)

        if is_self_deletion:
            user_to_delete = (
                self.db.query(User).filter(User.id == current_user.id).first()
            )
        else:
            if current_user.role.name != "admin":
                raise ForbiddenError("Không có quyền.")
            user_to_delete = self.db.query(User).filter(User.id == target_id).first()

            if not user_to_delete:
                raise NotFoundError("Không tìm thấy tài khoản.")

        user_info = (
            f"[{user_to_delete.id}, {user_to_delete.email}, {user_to_delete.role}]"
        )

        await self._revoke_all_user_tokens(user_to_delete.id)

        logger.info(f"Xóa tài khoản người dùng: {user_info} khỏi database.")
        self.db.delete(user_to_delete)
        self.db.commit()

        if is_self_deletion:
            logger.info(f"Tài khoản {user_info} đã tự xóa thành công.")
            return {
                "detail": "Tài khoản của bạn đã bị xóa vĩnh viễn khỏi hệ thống.",
                "self_deleted": True,
            }

        logger.info(
            f"Admin [{current_user.id}] đã xóa thành công tài khoản: {user_info}"
        )
        return {
            "detail": f"Đã xóa tài khoản {user_info} thành công khỏi hệ thống.",
            "self_deleted": False,
        }
