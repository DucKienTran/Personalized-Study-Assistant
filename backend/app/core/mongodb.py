from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


class MongoClientManager:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None

    def init_db(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_NAME]

    async def close_db(self):
        if self.client:
            self.client.close()


mongo_client = MongoClientManager()
