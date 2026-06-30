import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings 

# ==========================================
# PASSWORD HASHING
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ==========================================
#  JWT TOKEN HANDLER
# ==========================================
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
                    detail=f"Loại token không hợp lệ. Yêu cầu: {expected_type} token"
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