import time

from redis.asyncio import Redis

from app.core.config import settings

ONLINE_STATUS_EXPIRE_SECONDS = settings.ONLINE_STATUS_EXPIRE_SECONDS
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES


class PresenceService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def mark_online(self, user_id: int) -> None:
        await self.redis.setex(
            f"user:status:{user_id}", ONLINE_STATUS_EXPIRE_SECONDS, "online"
        )
        await self.redis.setex(
            f"user:last_active:{user_id}",
            REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            int(time.time()),
        )

    async def clear_online_status(self, user_id: int) -> None:
        await self.redis.delete(f"user:status:{user_id}")

    async def get_raw_presence(self, user_id: int) -> dict:
        status_val = await self.redis.get(f"user:status:{user_id}")
        last_active_raw = await self.redis.get(f"user:last_active:{user_id}")
        return {
            "is_online": bool(status_val),
            "last_active": int(last_active_raw) if last_active_raw else None,
        }
