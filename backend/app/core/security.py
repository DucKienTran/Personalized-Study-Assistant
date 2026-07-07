from datetime import datetime, timedelta, timezone
import time
from typing import List
import uuid

from fastapi import HTTPException, status
import jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.core.config import settings

# PASSWORD HASHING
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


#  JWT TOKEN HANDLER
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict) -> str:
    """
    Tạo Access Token.
    Payload 'data' truyền vào từ Service sẽ bao gồm: id, sub (email), role, jti
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Tạo Refresh Token.
    Payload 'data' truyền vào từ Service sẽ bao gồm: id, sub (email), role, jti
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_tokens_pair(user_id: int, email: str, role_name: str, permissions: List[str]) -> dict:
    """
    Hàm tạo cả cặp token Access & Refresh
    """
    token_jti = str(uuid.uuid4())

    access_payload = {
        "id": user_id,
        "sub": email,
        "role": role_name,
        "permissions": permissions,
        "jti": token_jti,
    }
    refresh_payload = {"id": user_id, "sub": email, "jti": token_jti}

    return {
        "access_token": create_access_token(access_payload),
        "refresh_token": create_refresh_token(refresh_payload),
        "token_type": "bearer",
        "jti": token_jti,
    }


def decode_token(token: str, expected_type: str, raise_on_error: bool = True) -> dict:
    try:
        # Giải mã token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Kiểm tra trường token_type
        token_type = payload.get("token_type")
        if token_type != expected_type:
            if raise_on_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Loại token không hợp lệ. Yêu cầu: {expected_type} token",
                )
            return None

        return payload

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        if raise_on_error:
            if isinstance(e, jwt.ExpiredSignatureError):
                detail = "Token đã hết hạn sử dụng"
            else:
                detail = "Token không hợp lệ hoặc đã bị thay đổi"

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

        return None


# blacklist token bằng Redis
async def blacklist_refresh_token(redis: Redis, token: str, exp: float) -> None:
    """Đưa refresh token vào blacklist trên Redis, TTL = thời gian còn lại đến khi token hết hạn tự nhiên."""
    ttl = int(exp - time.time())
    if ttl > 0:
        await redis.setex(f"blacklist:refresh:{token}", ttl, "true")


async def is_refresh_token_blacklisted(redis: Redis, token: str) -> bool:
    """Kiểm tra refresh token đã bị blacklist hay chưa."""
    return bool(await redis.get(f"blacklist:refresh:{token}"))
