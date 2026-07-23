from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    encoding="utf-8",
)


class MongoClientManager:
    def __init__(self):
        self.client: AsyncIOMotorClient | None = None
        self.db = None

    def init_db(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_NAME]

    async def close_db(self):
        if self.client:
            self.client.close()


mongo_client = MongoClientManager()
