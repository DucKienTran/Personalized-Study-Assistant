import time
import logging
from typing import Generator, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from redis.asyncio import Redis

from app.core.config import settings
from app.core.mysql import SessionLocal
from app.core.redis import redis_client
from app.models.user_model import UserModel
from app.core.security import decode_token

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Lấy cấu hình thời gian từ settings
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
ONLINE_STATUS_EXPIRE_SECONDS = settings.ONLINE_STATUS_EXPIRE_SECONDS

# ==========================================
# 1. Dependency cấp phát MySQL Session
# ==========================================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. Dependency cấp phát Redis Client
# ==========================================
async def get_redis() -> AsyncGenerator[Redis, None]:
    try:
        yield redis_client
    finally:
        pass

# ==========================================
# 3. Dependency xác thực & lấy thông tin User
# ==========================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token, expected_type="access")
    
    email = payload.get("sub")
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        logger.warning(f"Xác thực thất bại: Token hợp lệ nhưng không tìm thấy Email '{email}' trong Database.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Người dùng không tồn tại"
        )
        
    if not user.is_active:
        logger.warning(f"Truy cập bị chặn: Tài khoản [{user.id}, {user.email}] đang bị vô hiệu hóa.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tài khoản đã bị vô hiệu hóa."
        )

    await redis_client.setex(f"user:status:{user.id}", ONLINE_STATUS_EXPIRE_SECONDS, "online")
    await redis_client.setex(f"user:last_active:{user.id}", REFRESH_TOKEN_EXPIRE_MINUTES * 60, int(time.time()))

    return user