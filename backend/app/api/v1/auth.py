import logging
import time
from fastapi import APIRouter, Cookie, HTTPException, status, Response, Depends
from sqlalchemy.orm import Session
from redis.asyncio import Redis

from app.api.dependencies import get_db, get_redis
from app.core.config import settings
from app.models.user_model import User
from app.schemas.user_schema import UserRegister, UserResponse, UserLogin
from app.schemas.token_schema import TokenResponse
from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token, 
    decode_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
ONLINE_STATUS_EXPIRE_SECONDS = settings.ONLINE_STATUS_EXPIRE_SECONDS

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_client(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Đăng ký client thất bại: Email {user_data.email} đã tồn tại")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được đăng ký trên hệ thống."
        )
    
    hashed_pass = hash_password(user_data.password)
    
    new_user = User(
        email=user_data.email,
        password=hashed_pass,  
        role="client",
        full_name=user_data.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Đăng ký Client thành công: [{new_user.id}, {user_data.email}, {new_user.role}]")
    return new_user

@router.post("/register-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_admin(user_data: UserRegister, admin_key: str, db: Session = Depends(get_db)):
    if admin_key != settings.ADMIN_REGISTRATION_KEY:
        logger.warning(f"Đăng ký admin thất bại: Mã xác thực Admin không hợp lệ")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mã xác thực Admin không hợp lệ."
        )
    
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Đăng ký admin thất bại: Email {user_data.email} đã tồn tại")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được đăng ký trên hệ thống."
        )
    
    hashed_pass = hash_password(user_data.password)
    
    new_user = User(
        email=user_data.email,
        password=hashed_pass,  
        role="admin",
        full_name=user_data.full_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Đăng ký Admin thành công: [{new_user.id}, {user_data.email}, {new_user.role}]")
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login_user(
    response: Response, 
    form_data: UserLogin, 
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis) 
):  
    target_user = db.query(User).filter(User.email == form_data.email).first()
            
    if not target_user or not verify_password(form_data.password, target_user.password):
        logger.warning(f"Đăng nhập thất bại: Email {form_data.email} không tồn tại hoặc sai mật khẩu")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email hoặc mật khẩu không chính xác."
        )
        
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa."
        )
    
    token_payload = {"id": target_user.id, "sub": target_user.email, "role": target_user.role}
    
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)
    
    response.set_cookie(
        key="refresh_token", 
        value=refresh_token, 
        httponly=True, 
        secure=settings.COOKIE_SECURE, 
        samesite="lax", 
        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )

    await redis.setex(f"user:status:{target_user.id}", ONLINE_STATUS_EXPIRE_SECONDS, "online")
    await redis.setex(f"user:last_active:{target_user.id}", REFRESH_TOKEN_EXPIRE_MINUTES * 60, int(time.time()))

    logger.info(f"Đăng nhập với tư cách {target_user.role} thành công: [{target_user.id}, {target_user.email}, {target_user.role}]")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response, 
    refresh_token: str = Cookie(None), 
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis) # Tiêm Redis Client
):
    if not refresh_token:
        logger.warning(f"Không có Refresh Token trong Cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ (Missing Cookie)."
        )
    
    is_blacklisted = await redis.get(f"blacklist:refresh:{refresh_token}")
    if is_blacklisted:
        logger.warning(f"Phát hiện hành vi tái sử dụng Refresh Token: {refresh_token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên làm việc của bạn đã hết hạn hoặc thay đổi. Vui lòng đăng nhập lại."
        )
    
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload.get("id")
    user_email = payload.get("sub")
    user_role = payload.get("role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        logger.warning("Tài khoản không tồn tại, đã bị xóa hoặc vô hiệu hóa.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại, đã bị xóa hoặc vô hiệu hóa."
        )
    
    refresh_ttl = int(payload.get("exp") - time.time())
    if refresh_ttl > 0:
        await redis.setex(f"blacklist:refresh:{refresh_token}", refresh_ttl, "true")
    
    new_payload = {"id": user_id, "sub": user_email, "role": user_role}

    response.set_cookie(
        key="refresh_token", 
        value=create_refresh_token(new_payload), 
        httponly=True, 
        secure=settings.COOKIE_SECURE, 
        samesite="lax", 
        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )

    logger.info(f"Cấp lại token thành công cho người dùng: [{user_id}, {user_email}, {user_role}]")
    return {"access_token": create_access_token(new_payload), "token_type": "bearer"}

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    response: Response, 
    refresh_token: str = Cookie(None),
    redis: Redis = Depends(get_redis) 
): 
    if refresh_token:
        payload_refresh = decode_token(refresh_token, expected_type="refresh", raise_on_error=False)

        if payload_refresh:
            refresh_ttl = int(payload_refresh.get("exp") - time.time())
            if (refresh_ttl > 0):
                await redis.setex(f"blacklist:refresh:{refresh_token}", refresh_ttl, "true")

            user_id = payload_refresh.get("id")
            user_email = payload_refresh.get("sub")
            user_role = payload_refresh.get("role")

            await redis.setex(f"user:last_active:{user_id}", REFRESH_TOKEN_EXPIRE_MINUTES * 60, int(time.time()))
            await redis.delete(f"user:status:{user_id}")

            logger.info(f"Người dùng đăng xuất thành công. Tài khoản [{user_id}, {user_email}, {user_role}] đã bị vô hiệu hóa Refresh Token.")
        else:
            logger.warning("Phát hiện request logout kèm theo Refresh Token lỗi cấu trúc.")

    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")
    return {"detail": "Đăng xuất thành công."}