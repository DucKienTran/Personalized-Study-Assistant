import os

from bson import ObjectId
import google.generativeai as genai

from app.ai.prompt_builder import SummaryPromptBuilder


class AISummarizerService:
    def __init__(self, mongo_db):
        self.collection = mongo_db["parsed_documents"]

        # Lấy key từ file .env và khởi động AI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("CẢNH BÁO: Chưa có GEMINI_API_KEY. Vui lòng kiểm tra file .env")

        genai.configure(api_key=api_key)
        # Sử dụng model gemini-1.5-flash: Rất nhanh, rẻ/miễn phí, xử lý text dài cực tốt
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def generate_summary(self, mongo_id: str, level: str, format_type: str, instruction: str):
        doc = await self.collection.find_one({"_id": ObjectId(mongo_id)})
        if not doc or "content_raw" not in doc:
            raise ValueError("Không tìm thấy nội dung tài liệu trong MongoDB")

        content_raw = doc["content_raw"]

        # 2. Tạo Cache Key
        safe_instruction = instruction.strip().replace(".", "").replace(" ", "_")[:20]
        cache_key = f"{level}_{format_type}_{safe_instruction}".lower()

        # 3. Kiểm tra Cache
        if "summaries" in doc and cache_key in doc["summaries"]:
            print(f"[Cache Hit] Đã trả về kết quả cũ cho config: {cache_key}")
            return doc["summaries"][cache_key]

        # 4. Nếu chưa có Cache -> Build Prompt
        prompt = SummaryPromptBuilder.build(content_raw, level, format_type, instruction)

        # --- ĐÂY LÀ ĐOẠN GỌI AI THẬT ---
        try:
            print("[AI Gọi] Đang nhờ Gemini đọc và tóm tắt...")
            # Gọi Gemini xử lý prompt bất đồng bộ (async)
            response = await self.model.generate_content_async(prompt)
            ai_response = response.text
        except Exception as e:
            print(f"Lỗi khi gọi AI: {e}")
            raise ValueError("Có lỗi xảy ra khi kết nối với AI. Vui lòng thử lại sau.")
        # -------------------------------

        # 5. Lưu kết quả mới vào MongoDB
        await self.collection.update_one(
            {"_id": ObjectId(mongo_id)}, {"$set": {f"summaries.{cache_key}": ai_response}}
        )

        return ai_response
