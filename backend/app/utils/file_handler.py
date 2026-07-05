import os
import re

from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "uploads"))


def validate_and_save_file(file: UploadFile) -> str:
    """
    Kiểm tra định dạng và lưu file vào thư mục uploads.
    Trả về đường dẫn tuyệt đối của file đã lưu.
    """
    # Kiểm tra
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng file không được hỗ trợ. Chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Lưu file
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # xóa ký tự đặc biệt trong tên
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", os.path.splitext(filename)[0])
    safe_filename = f"{clean_name}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lưu file lên server: {str(e)}")

    return file_path


# Xóa file
def delete_physical_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path)
