from contextlib import asynccontextmanager
import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import configure_mappers
from sqlalchemy.sql import text

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.quizzes import attempts_router as quiz_attempts_router
from app.api.quizzes import router as quizzes_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.database import Base, engine, mongo_client, redis_client
from app.core.logging import setup_logging
from app.exceptions import AppError, app_exception_handler
import app.models

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo MySQL Database
    try:
        logger.info("Đang kiểm tra và ánh xạ mapping cấu trúc các Model...")
        configure_mappers()
        logger.info("SQLAlchemy: Mapping cấu trúc các Model thành công!")

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

    # Khởi tạo MongoDB Database
    try:
        mongo_client.init_db()
        logger.info("Kết nối MongoDB thành công.")
    except Exception as e:
        logger.critical(f"LỖI KẾT NỐI DATABASE MONGODB: {str(e)}")
        raise e

    yield

    logger.info("Đang dọn dẹp tài nguyên trước khi tắt server...")
    await redis_client.aclose()
    await mongo_client.close_db()
    engine.dispose()
    logger.info("Server đã tắt an toàn.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Core API backend cho Study Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(AppError, app_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"CRASH HỆ THỐNG: Lỗi tại {request.method} {request.url.path}")
    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Đã xảy ra lỗi hệ thống nghiêm trọng. Vui lòng liên hệ Admin.",
            "path": request.url.path,
        },
    )


app.include_router(auth_router, prefix=settings.API_STR)
app.include_router(users_router, prefix=settings.API_STR)
app.include_router(documents_router, prefix=settings.API_STR)
app.include_router(quizzes_router, prefix=settings.API_STR)
app.include_router(quiz_attempts_router, prefix=settings.API_STR)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "StudyAIssistant API is running!"}
