from datetime import datetime, timedelta, timezone
import time

from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user_activity_model import UserDailyActivity

ONLINE_STATUS_EXPIRE_SECONDS = settings.ONLINE_STATUS_EXPIRE_SECONDS
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES

# The browser sends one heartbeat every 60 seconds while the document is visible.
# A 120-second Redis TTL means a long-hidden/closed tab starts a fresh interval
# instead of receiving credit for time spent away from the app.
HEARTBEAT_TTL_SECONDS = 120
MAX_CREDIT_SECONDS = 90

# Atomic get-old + set-new prevents multiple open tabs from double-counting the
# same minute for one user.
_HEARTBEAT_LUA = """
local previous = redis.call('GET', KEYS[1])
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
if not previous then
  return 0
end
local elapsed = tonumber(ARGV[1]) - tonumber(previous)
if elapsed <= 0 or elapsed > tonumber(ARGV[3]) then
  return 0
end
return elapsed
"""


class PresenceService:
    def __init__(self, redis: Redis, db: Session | None = None):
        self.redis = redis
        self.db = db

    async def mark_online(self, user_id: int) -> None:
        await self.redis.setex(f"user:status:{user_id}", ONLINE_STATUS_EXPIRE_SECONDS, "online")
        await self.redis.setex(
            f"user:last_active:{user_id}",
            REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            int(time.time()),
        )

    async def heartbeat(self, user_id: int, timezone_offset_minutes: int = 0) -> int:
        """Record one visible-browser activity heartbeat and return credited seconds."""
        if self.db is None:
            raise RuntimeError("PresenceService requires a database session for heartbeat tracking")

        # Keep the existing online/last-active semantics in sync with heartbeat activity.
        await self.mark_online(user_id)

        now_epoch = int(time.time())
        heartbeat_key = f"user:heartbeat:{user_id}"
        credited = int(
            await self.redis.eval(
                _HEARTBEAT_LUA,
                1,
                heartbeat_key,
                now_epoch,
                HEARTBEAT_TTL_SECONDS,
                MAX_CREDIT_SECONDS,
            )
        )
        if credited <= 0:
            return 0

        # JS getTimezoneOffset has the opposite sign, so the frontend sends the
        # already-normalized offset: UTC+7 => +420.
        local_now = datetime.now(timezone.utc) + timedelta(minutes=timezone_offset_minutes)
        activity_date = local_now.date()

        row = (
            self.db.query(UserDailyActivity)
            .filter(
                UserDailyActivity.user_id == user_id,
                UserDailyActivity.activity_date == activity_date,
            )
            .first()
        )
        if row is None:
            row = UserDailyActivity(
                user_id=user_id,
                activity_date=activity_date,
                active_seconds=credited,
            )
            self.db.add(row)
        else:
            row.active_seconds += credited

        self.db.commit()
        return credited

    async def clear_online_status(self, user_id: int) -> None:
        await self.redis.delete(f"user:status:{user_id}")
        await self.redis.delete(f"user:heartbeat:{user_id}")

    async def get_raw_presence(self, user_id: int) -> dict:
        status_val = await self.redis.get(f"user:status:{user_id}")
        last_active_raw = await self.redis.get(f"user:last_active:{user_id}")
        return {
            "is_online": bool(status_val),
            "last_active": int(last_active_raw) if last_active_raw else None,
        }
