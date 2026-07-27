from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.models.user_model import RefreshToken
from app.services.presence_service import PresenceService


class TokenService:
    def __init__(
        self,
        db: Session,
        redis: Redis,
        presence: PresenceService,
    ):
        self.db = db
        self.redis = redis
        self.presence = presence

    def save_refresh_token(
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

    async def revoke_all_user_tokens(
        self,
        user_id: int,
        revoke_db_tokens: bool = False,
    ) -> None:
        await self.redis.setex(
            f"user:revoked:{user_id}",
            86400 * 7,
            "true",
        )

        await self.presence.clear_online_status(user_id)

        if revoke_db_tokens:
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

    def revoke_refresh_token(
        self,
        jti: str,
    ) -> None:
        db_token = self.db.query(RefreshToken).filter(RefreshToken.jti == jti).first()

        if db_token:
            db_token.revoked = True
            self.db.commit()
