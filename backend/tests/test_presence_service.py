import pytest

from app.models.user_model import User
from app.services.presence_service import PresenceService


class FakeUser:
    def __init__(self, user_id: int, is_active: int = 0):
        self.id = user_id
        self.is_active = is_active


class FakeQueryResult:
    def __init__(self, user):
        self.user = user

    def filter(self, *args, **kwargs):
        return self

    def update(self, values, synchronize_session=False):
        self.user.is_active = values[User.is_active]


class FakeDB:
    def __init__(self, user):
        self.user = user
        self.commit_calls = 0

    def query(self, *args, **kwargs):
        return FakeQueryResult(self.user)

    def commit(self):
        self.commit_calls += 1


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def get(self, key):
        return self.store.get(key)


@pytest.mark.asyncio
async def test_mark_online_and_clear_offline_persist_to_db_and_redis():
    user = FakeUser(user_id=1, is_active=0)
    db = FakeDB(user)
    redis = FakeRedis()
    service = PresenceService(db, redis)

    await service.mark_online(1)
    assert user.is_active == 1
    assert await redis.get("user:status:1") == "online"

    await service.clear_online_status(1)
    assert user.is_active == 0
    assert await redis.get("user:status:1") is None
    assert db.commit_calls >= 2
