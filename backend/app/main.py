import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import text

import app.models
from app.api.v1.users import router as users_router
from app.api.v1.auth import router as auth_router
from app.core.mysql import engine, Base
from app.core.redis import redis_client
from app.core.config import settings
from app.core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo MySQL Database
    try:
        Base.metadata.create_all(bind=engine)

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Kết nối MySQL Database thành công.")
    except Exception as e:
        logger.critical(f"LỖI KẾT NỐI DATABASE MYSQL: {str(e)}")
        raise e

    # Khởi tạo Redis Database 
    try:
        await redis_client.ping()
        logger.info("Kết nối Redis thành công.")
    except Exception as e:
        logger.critical(f"LỖI KẾT NỐI REDIS: {str(e)}")
        raise e
        
    yield
    
    logger.info("Đang dọn dẹp tài nguyên trước khi tắt server...")
    await redis_client.aclose()
    engine.dispose()
    logger.info("Server đã tắt an toàn.")

# ==========================================
# KHỞI TẠO ỨNG DỤNG
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME, 
    description="Core API backend cho Study Assistant",
    version="1.0.0",
    lifespan=lifespan # Inject lifespan vào app
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            
    allow_credentials=True,
    allow_methods=["*"],              
    allow_headers=["*"],              
)

# EXCEPTION HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"CRASH HỆ THỐNG: Lỗi tại {request.method} {request.url.path}")
    logger.error(traceback.format_exc()) 
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Đã xảy ra lỗi hệ thống nghiêm trọng. Vui lòng liên hệ Admin.",
            "path": request.url.path
        }
    )


app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "StudyAIssistant API is running!"}