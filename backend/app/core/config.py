from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "LearningAId"
    API_V1_STR: str = "/api/v1"

    # Secret
    GEMINI_API_KEY: str
    JWT_SECRET_KEY: str
    ADMIN_REGISTRATION_KEY: str

    # Database MySQL Config
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str = ""
    DB_NAME: str

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cấu hình Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Cấu hình MongoDB
    MONGODB_HOST: str = "localhost" 
    MONGODB_PORT: int = 27017
    MONGODB_NAME: str

    @property
    def MONGODB_URL(self) -> str:
        return f"mongodb://{self.MONGODB_HOST}:{self.MONGODB_PORT}"


    # Token & Security Config
    JWT_ALGORITHM: str = "HS256"
    COOKIE_SECURE: bool = False

    # expired time
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    ONLINE_STATUS_EXPIRE_SECONDS: int = 300


settings = Settings()
