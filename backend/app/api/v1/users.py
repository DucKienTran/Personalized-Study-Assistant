import time
import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Cookie, HTTPException, Response, status, Depends
from sqlalchemy.orm import Session
from redis.asyncio import Redis

from app.api.dependencies import get_db, get_redis, get_current_user
from app.core.config import settings
from app.models.user_model import User
from app.schemas.user_schema import UserResponse, ChangePassword, UserStatus
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES

# ==========================================
# API get me
# ==========================================
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    logger.info(f"Truy cập thông tin cá nhân thành công: {current_user.id}, {current_user.email}, {current_user.role}")
    return current_user

# ==========================================
# API get all
# ==========================================
@router.get("/all", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        logger.warning(
            f"Truy cập trái phép: Người dùng [{current_user.id}, {current_user.email}, {current_user.role}] "
            f"cố gắng truy cập API lấy toàn bộ danh sách users")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập vào danh sách người dùng (Yêu cầu quyền Admin)."
        )
    
    logger.info(f"Truy cập danh sách người dùng thành công: ADMIN [{current_user.id}, {current_user.email}]")
    users = db.query(User).all()
    return users

# ==========================================
# Helper: Xử lý logic trạng thái Online/Offline
# ==========================================
async def _format_user_status(target_user: User, redis: Redis) -> dict:
    """Hàm helper để tính toán trạng thái và thời gian offline của một user"""
    user_id = target_user.id
    user_email = target_user.email 
    user_role = target_user.role
    
    status_val = await redis.get(f"user:status:{user_id}")
    last_active_raw = await redis.get(f"user:last_active:{user_id}")
    last_active_int = int(last_active_raw) if last_active_raw else None

    # Trạng thái Online
    if status_val:
        return {
            "user_id": user_id, 
            "email": user_email, 
            "role": user_role,
            "status": "online", 
            "message": "Đang hoạt động",
            "last_active": last_active_int
        }

    # Trạng thái Offline quá thời gian lưu trữ cache hoặc chưa từng online
    if not last_active_int:
        return {
            "user_id": user_id, 
            "email": user_email, 
            "role": user_role,
            "status": "offline", 
            "message": "Không hoạt động",
            "last_active": None
        }
    
    # Offline trong thời gian gần đây (Có lưu cache)
    seconds_offline = int(time.time()) - last_active_int
    ONE_MINUTE, ONE_HOUR, ONE_DAY = 60, 3600, 86400

    if seconds_offline < ONE_HOUR:
        message = f"Hoạt động {seconds_offline // ONE_MINUTE} phút trước" 
    elif seconds_offline < ONE_DAY:
        message = f"Hoạt động {seconds_offline // ONE_HOUR} giờ trước"
    else:
        message = f"Hoạt động {seconds_offline // ONE_DAY} ngày trước"
    
    return {
        "user_id": user_id, 
        "email": user_email, 
        "role": user_role,
        "status": "offline", 
        "message": message,
        "last_active": last_active_int
    }

# ==========================================
# API Check Status
# ==========================================
@router.get("/get-status", status_code=status.HTTP_200_OK, response_model=Union[UserStatus, List[UserStatus]]) 
async def get_user_status(
    target_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    if current_user.role != "admin":
        logger.warning(f"Cảnh báo bảo mật: User [{current_user.id}] cố gắng truy cập tính năng xem trạng thái.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Bạn không có quyền xem trạng thái của người dùng (Yêu cầu quyền Admin)."
        )
    
    # Xem cho 1 người
    if target_id:
        target_user = db.query(User).filter(User.id == target_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng này.")
        
        return await _format_user_status(target_user, redis)
    
    # Xem tất cả mọi người
    all_users = db.query(User).all()
    all_statuses = [await _format_user_status(u, redis) for u in all_users]
    
    return all_statuses
    
# ==========================================
# API Đổi mật khẩu
# ==========================================
@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePassword, 
    response: Response,
    current_user: User = Depends(get_current_user), 
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    # Kiểm tra mật khẩu cũ
    if not verify_password(data.old_password, current_user.password):
        logger.warning(f"Đổi mật khẩu thất bại: Tài khoản [{current_user.id}] nhập sai mật khẩu cũ.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu cũ không chính xác."
        )
    
    # Kiểm tra mật khẩu mới
    if verify_password(data.new_password, current_user.password):
        logger.warning(f"Đổi mật khẩu thất bại: Tài khoản [{current_user.id}] nhập mật khẩu mới trùng với mật khẩu cũ.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới không được trùng với mật khẩu cũ."
        )
    
    if not refresh_token:
        logger.warning(f"Không có Refresh Token trong Cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ (Missing Cookie)."
        )
    
    # Kiểm tra Blacklist trên Redis
    is_blacklisted = await redis.get(f"blacklist:refresh:{refresh_token}")
    if is_blacklisted:
        logger.warning(f"Phát hiện hành vi tái sử dụng Refresh Token: {refresh_token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Phiên làm việc của bạn đã hết hạn hoặc thay đổi. Vui lòng đăng nhập lại."
        )
    
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload.get("id") != current_user.id:
        logger.error(f"CẢNH BÁO: Phát hiện bất đồng bộ định danh! "
                     f"Access Token ID [{current_user.id}] gửi kèm Refresh Token ID [{payload.get('id')}].")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thông tin xác thực không đồng nhất."
        )
    
    user_id = current_user.id
    user_email = current_user.email
    user_role = current_user.role

    # Băm mật khẩu mới và cập nhật
    current_user.password = hash_password(data.new_password)
    db.commit()
    
    logger.info(f"Đổi mật khẩu thành công cho tài khoản: [{user_id}, {user_email}, {user_role}]")

    # Đưa token cũ vào blacklist
    refresh_ttl = int(payload.get("exp") - time.time())
    if refresh_ttl > 0:
        await redis.setex(f"blacklist:refresh:{refresh_token}", refresh_ttl, "true")
    
    new_payload = { 
        "id": user_id,
        "sub": user_email, 
        "role": user_role
    }

    # Cấp lại token mới luôn cho Client
    response.set_cookie(
        key="refresh_token",
        value=create_refresh_token(new_payload),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60
    )

    logger.info(f"Cấp lại token thành công cho người dùng [{user_id}, {user_email}, {user_role}] sau khi đổi mật khẩu")
    
    return {
        "access_token": create_access_token(new_payload),
        "token_type": "bearer",
        "detail": "Thay đổi mật khẩu thành công."
    }

# ==========================================
# API Xóa tài khoản
# ==========================================
@router.delete("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    response: Response,
    target_id: Optional[int] = None,  
    refresh_token: str = Cookie(None),  
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    is_self_deletion = (target_id is None) or (target_id == current_user.id)
    
    if is_self_deletion:
        user_to_delete = current_user
    else:
        if current_user.role != "admin":
            logger.warning(f"Cảnh báo: Người dùng [{current_user.id}] cố gắng xóa tài khoản [{target_id}] mà không có quyền.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Bạn không có quyền xóa tài khoản của người khác."
            )
        
        user_to_delete = db.query(User).filter(User.id == target_id).first()
        if not user_to_delete:
            logger.warning("Không tìm thấy tài khoản cần xóa trong database")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản cần xóa.")

    user_info = f"[{user_to_delete.id}, {user_to_delete.email}, {user_to_delete.role}]"

    # Xóa dữ liệu về trạng thái trên Redis
    await redis.delete(f"user:status:{user_to_delete.id}")
    await redis.delete(f"user:last_active:{user_to_delete.id}")

    # Xóa MySQL
    logger.info(f"Xóa tài khoản người dùng: {user_info} khỏi database.")
    db.delete(user_to_delete)
    db.commit()
    
    if is_self_deletion:
        logger.info(f"Xóa Refresh Token khỏi Cookie HttpOnly cho tài khoản: {user_info}")
        response.delete_cookie(key="refresh_token", httponly=True, samesite="lax")

        if refresh_token:
            payload_refresh = decode_token(refresh_token, expected_type="refresh", raise_on_error=False)
            if payload_refresh:
                refresh_ttl = int(payload_refresh.get("exp", 0) - time.time())
                if refresh_ttl > 0:
                    await redis.setex(f"blacklist:refresh:{refresh_token}", refresh_ttl, "true")

        logger.info(f"Tài khoản {user_info} đã tự xóa thành công.")
        return {"detail": "Tài khoản của bạn đã bị xóa vĩnh viễn khỏi hệ thống."}

    logger.info(f"Admin [{current_user.id}] đã xóa thành công tài khoản: {user_info}")
    return {"detail": f"Đã xóa tài khoản {user_info} thành công khỏi hệ thống."}