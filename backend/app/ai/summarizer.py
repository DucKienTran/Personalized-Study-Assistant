import os

from bson import ObjectId
from fastapi import HTTPException
import google.generativeai as genai

from app.ai.prompt_builder import SummaryPromptBuilder


class AISummarizerService:
    def __init__(self, mongo_db):
        self.collection = mongo_db["parsed_documents"]

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("CẢNH BÁO: Chưa có GEMINI_API_KEY. Vui lòng kiểm tra file .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")

    async def generate_summary(self, mongo_id: str, level: str, format_type: str, instruction: str):
        doc = await self.collection.find_one({"_id": ObjectId(mongo_id)})
        if not doc or "content_raw" not in doc:
            raise ValueError("Không tìm thấy nội dung tài liệu trong MongoDB")

        content_raw = doc["content_raw"]

        safe_instruction = instruction.strip().replace(".", "").replace(" ", "_")[:20]
        cache_key = f"{level}_{format_type}_{safe_instruction}".lower()

        if "summaries" in doc and cache_key in doc["summaries"]:
            print(f"[Cache Hit] Đã trả về kết quả cũ cho config: {cache_key}")
            return doc["summaries"][cache_key]

        prompt = SummaryPromptBuilder.build(content_raw, level, format_type, instruction)

        # --- ĐÂY LÀ ĐOẠN GỌI AI THẬT ---
        try:
            print("[AI Gọi] Đang nhờ Gemini đọc và tóm tắt...")
            response = await self.model.generate_content_async(prompt)

            if not response or not response.text:
                print(f"⚠️ Gemini trả về rỗng! Toàn bộ Object phản hồi: {response}")
                raise ValueError(
                    "Gemini không trả về nội dung. Có thể do bị chặn nội dung (Safety)."
                )

            ai_response = response.text
            print(f"🎉 AI phản hồi thành công! Độ dài: {len(ai_response)} ký tự.")

        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi gọi AI: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Có lỗi xảy ra khi kết nối với AI: {str(e)}"
            )

        await self.collection.update_one(
            {"_id": ObjectId(mongo_id)},
            {"$set": {f"summaries.{cache_key}": ai_response}},
        )

        return ai_response
