import json
import logging
import secrets

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    blacklist_refresh_token,
    decode_token,
    generate_tokens_pair,
    hash_password,
    hash_token,
    is_refresh_token_blacklisted,
    verify_password,
)
from app.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user_model import RefreshToken, Role, User
from app.schemas.user_schema import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserLogin,
    UserRegister,
    VerifyEmailRequest,
)
from app.services.email_service import EmailService
from app.services.presence_service import PresenceService
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        db: Session,
        redis: Redis,
        presence: PresenceService,
        email_service: EmailService,
    ):
        self.db = db
        self.redis = redis
        self.presence = presence
        self.email_service = email_service

        self.token_service = TokenService(
            db=db,
            redis=redis,
            presence=presence,
        )

    # auth_service.py — sửa lại register()
    async def register(
        self, user_data: UserRegister, role_name: str = "client"
    ) -> dict:
        uniform_message = {
            "detail": "If this email is valid, a message with next steps has been sent."
        }

        ratelimit_key = f"register_ratelimit:{user_data.email}"
        if await self.redis.exists(ratelimit_key):
            return uniform_message
        await self.redis.setex(ratelimit_key, 60, "1")

        existing_user = (
            self.db.query(User).filter(User.email == user_data.email).first()
        )
        if existing_user:
            logger.info(f"Registration attempted for existing email: {user_data.email}")
            await self.email_service.send_already_registered_email(
                to_email=existing_user.email,
                full_name=existing_user.full_name,
            )
            return uniform_message

        db_role = self.db.query(Role).filter(Role.name == role_name).first()
        if not db_role:
            logger.error(f"System configuration missing role '{role_name}'")
            raise InternalServerError(
                f"System configuration error: Role '{role_name}' does not exist."
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)

        payload = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password_hash": hash_password(user_data.password),
            "role_name": role_name,
        }

        redis_key = f"pending_register:{token_hash}"
        await self.redis.setex(
            redis_key,
            settings.PENDING_REGISTER_TTL_SECONDS,
            json.dumps(payload),
        )

        await self.email_service.send_verification_email(
            to_email=user_data.email,
            full_name=user_data.full_name,
            token=raw_token,
        )

        logger.info(f"Pending registration saved to Redis for email: {user_data.email}")
        return uniform_message

    async def verify_email(self, data: VerifyEmailRequest) -> dict:
        token_hash = hash_token(data.token)
        redis_key = f"pending_register:{token_hash}"

        raw_payload = await self.redis.get(redis_key)
        if not raw_payload:
            raise BadRequestError("Invalid or expired verification link.")

        payload = json.loads(raw_payload)
        email = payload["email"]

        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            await self.redis.delete(redis_key)
            raise ConflictError("This email address is already registered.")

        db_role = self.db.query(Role).filter(Role.name == payload["role_name"]).first()
        if not db_role:
            raise InternalServerError(
                "System configuration error: Role does not exist."
            )

        new_user = User(
            email=email,
            password_hash=payload["password_hash"],
            role=db_role,
            full_name=payload.get("full_name"),
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        await self.redis.delete(redis_key)

        logger.info(f"User created after email verification: [{new_user.id}, {email}]")
        return {"detail": "Email verified successfully. You can now log in."}

    async def forgot_password(self, data: ForgotPasswordRequest) -> dict:
        uniform_message = "A password reset link has been sent to your email."

        user = self.db.query(User).filter(User.email == data.email).first()
        if not user:
            return {"detail": uniform_message}

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)

        redis_key = f"password_reset:{token_hash}"
        payload = {"user_id": user.id}

        await self.redis.setex(
            redis_key,
            settings.PASSWORD_RESET_TTL_SECONDS,
            json.dumps(payload),
        )

        await self.email_service.send_password_reset_email(
            to_email=user.email,
            full_name=user.full_name,
            token=raw_token,
        )

        return {"detail": uniform_message}

    async def reset_password(self, data: ResetPasswordRequest) -> dict:
        token_hash = hash_token(data.token)
        redis_key = f"password_reset:{token_hash}"

        raw_payload = await self.redis.get(redis_key)
        if not raw_payload:
            raise BadRequestError("Invalid or expired password reset link.")

        payload = json.loads(raw_payload)
        user_id = payload["user_id"]

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            await self.redis.delete(redis_key)
            raise NotFoundError("User not found.")

        user.password_hash = hash_password(data.new_password)
        self.db.commit()

        await self.redis.delete(redis_key)
        await self.token_service.revoke_all_user_tokens(user_id, revoke_db_tokens=True)

        logger.info(f"Password reset successfully for user_id={user_id}")
        return {
            "detail": "Password reset successfully. Please log in with your new password."
        }

    async def login(self, form_data: UserLogin, request: Request) -> dict:
        target_user = self.db.query(User).filter(User.email == form_data.email).first()

        if not target_user:
            logger.warning(f"Login failed: Email {form_data.email} not found")
            raise UnauthorizedError("Invalid email or password.")
        if not verify_password(form_data.password, target_user.password_hash):
            logger.warning(f"Login failed: Incorrect password for {form_data.email}")
            raise UnauthorizedError("Invalid email or password.")

        if not target_user.is_active:
            raise ForbiddenError("Account has been disabled.")
        await self.redis.delete(f"user:revoked:{target_user.id}")

        tokens = generate_tokens_pair(
            user_id=target_user.id,
            email=target_user.email,
            role_name=target_user.role.name,
            permissions=[p.name for p in target_user.role.permissions],
            remember_me=form_data.remember_me,
        )

        self.token_service.save_refresh_token(
            user_id=target_user.id,
            refresh_token=tokens["refresh_token"],
            jti=tokens["jti"],
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )
        await self.presence.mark_online(target_user.id)

        logger.info(
            f"User [{target_user.id}, {target_user.email}] logged in successfully. JTI: {tokens['jti']}"
        )
        return tokens

    async def refresh(self, refresh_token: str, request: Request) -> dict:
        if not refresh_token:
            raise UnauthorizedError(
                "Session has expired or is invalid (Missing Cookie)."
            )

        if await is_refresh_token_blacklisted(self.redis, refresh_token):
            try:
                payload = decode_token(
                    refresh_token, expected_type="refresh", raise_on_error=False
                )
                if payload and payload.get("id"):
                    await self.token_service.revoke_all_user_tokens(payload.get("id"))
            except Exception as e:
                logger.error(f"Error revoking user tokens: {str(e)}")

            raise UnauthorizedError("Security token blacklisted. Please log in again.")

        payload = decode_token(refresh_token, expected_type="refresh")
        remember_me = payload.get("remember_me", False)

        db_token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.jti == payload["jti"])
            .first()
        )

        if not db_token:
            raise UnauthorizedError("Refresh token does not exist.")

        if db_token.revoked:
            raise UnauthorizedError("Refresh token has been revoked.")
        user_id = payload.get("id")

        if await self.redis.exists(f"user:revoked:{user_id}"):
            raise UnauthorizedError("Session has been revoked. Please log in again.")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise UnauthorizedError("User does not exist or account is disabled.")

        await blacklist_refresh_token(self.redis, refresh_token, payload.get("exp"))
        self.token_service.revoke_refresh_token(payload.get("jti"))

        new_tokens = generate_tokens_pair(
            user_id=user.id,
            email=user.email,
            role_name=user.role.name,
            permissions=[p.name for p in user.role.permissions],
            remember_me=remember_me,
        )
        new_tokens["remember_me"] = remember_me

        self.token_service.save_refresh_token(
            user_id=user.id,
            refresh_token=new_tokens["refresh_token"],
            jti=new_tokens["jti"],
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )
        await self.presence.mark_online(user.id)

        logger.info(
            f"Token refreshed for user: [{user.id}, {user.email}]. Old JTI: {payload.get('jti')} -> New JTI: {new_tokens['jti']}"
        )
        return new_tokens

    async def logout(self, refresh_token: str) -> dict:
        if refresh_token:
            payload = decode_token(
                refresh_token, expected_type="refresh", raise_on_error=False
            )
            if payload:
                await blacklist_refresh_token(
                    self.redis, refresh_token, payload.get("exp")
                )
                user_id = payload.get("id")
                await self.presence.clear_online_status(user_id)
                self.token_service.revoke_refresh_token(payload.get("jti"))
                logger.info(f"User logged out: user_id={user_id}")

        return {"detail": "Logged out successfully."}
