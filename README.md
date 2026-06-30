# AI Learning Assistant

> Hệ thống hỗ trợ học tập thông minh, cho phép người dùng tải lên tài liệu bài giảng để AI tự động xử lý nội dung.

**Lưu ý:** Hệ thống chỉ có 1 role duy nhất, không phân chia giáo viên hay học sinh — người dùng có thể vừa tạo đề, vừa tự làm bài, vừa tự chấm.

## 1. Mô tả

### Chức năng chính

- Tóm tắt tài liệu học tập
- Tạo bài kiểm tra từ nội dung tài liệu
- Chấm điểm và đánh giá kết quả bài kiểm tra
- Hỏi đáp trực tiếp dựa trên tài liệu đã tải lên

### Input

- Giáo trình
- Slide bài giảng (PDF)

### Output

- Nội dung tóm tắt
- Bộ câu hỏi kiểm tra
- Kết quả chấm điểm
- Câu trả lời cho các câu hỏi liên quan đến tài liệu

## 2. Workflow

**Bước 1 — Đăng nhập**
Người dùng đăng nhập vào hệ thống bằng JWT Auth.

**Bước 2 — Upload tài liệu**
Người dùng tải lên file (PDF, slide...) và gán nhãn thủ công:
- Loại tài liệu: giáo trình/tài liệu học tập, đề mẫu/đáp án, hoặc tài liệu tham khảo bổ sung.
- Môn học: hệ thống gợi ý dựa trên tên file và nội dung trang đầu, người dùng xác nhận hoặc sửa lại.

**Bước 3 — Trích xuất nội dung** (chạy một lần sau khi upload)
Hệ thống parse file, trích xuất toàn bộ text, hình ảnh, cấu trúc trang.

**Bước 4 — Phân loại tài liệu**
Hệ thống tự động phân tích:
- Mục đích tài liệu: khai thác nội dung để học hay chỉ tham khảo cấu trúc/form.
- Tài liệu có đủ kiến thức để sinh câu hỏi tự luận không.
- Tài liệu có chứa hình ảnh có ý nghĩa học tập không, phân biệt hình minh họa và hình chứa kiến thức.

Kết quả phân loại quyết định module nào được unlock ở bước tiếp theo.

**Bước 5 — Tạo embedding và lưu vào database**
Nội dung text và hình ảnh có ý nghĩa được tạo vector embedding, lưu vào MongoDB phục vụ RAG. Metadata lưu vào MySQL.

**Bước 6 — Người dùng chọn chức năng**
Dựa trên kết quả phân loại, hệ thống hiển thị các module khả dụng. Người dùng chọn một trong 4 chức năng độc lập:

- **6.1 Tóm tắt tài liệu** — AI tóm tắt nội dung theo chủ đề, lưu kết quả, hiển thị lên web.
- **6.2 Kiểm tra** — AI sinh bộ câu hỏi và đáp án mẫu (Multiple Choice, Fill in the Blank, True/False, tự luận), có thể export PDF/DOCX, hiển thị form để người dùng làm bài trực tiếp trên web.
- **6.3 Chấm bài** — chấm tự động với câu hỏi khách quan, AI chấm theo rubric với tự luận, hoặc đối chiếu bài làm upload độc lập với tài liệu gốc.
- **6.4 Hỏi đáp theo tài liệu** — chat hỏi đáp dựa trên RAG, AI trả lời kèm trích dẫn nội dung liên quan.

**Bước 7 — Thống kê kết quả**
Tổng hợp hoạt động người dùng: lịch sử hỏi đáp, tài liệu đã tóm tắt, điểm số và lịch sử làm bài. Hiển thị biểu đồ tiến độ học tập, cập nhật realtime qua WebSocket/SSE.

**Hệ thống nền** (chạy xuyên suốt)
Redis cache kết quả và session, LangChain/Mastra Agent điều phối tác vụ AI, Docker và Nginx triển khai hệ thống, CI/CD quản lý log và deploy.

### Database

| Database | Vai trò |
|----------|---------|
| **MySQL** | Tài khoản, thông tin file, đề kiểm tra, kết quả chấm điểm |
| **MongoDB** | Nội dung trích xuất từ tài liệu, bản tóm tắt, lịch sử chat, dữ liệu sync lưu trữ dài hạn |
| **Redis** | Cache JWT/blacklist token, cache kết quả AI, hỗ trợ truyền dữ liệu realtime (WebSocket/SSE) |

## 3. Cấu trúc thư mục

```
learning-aid/
├── backend/
│   ├── alembic/                # Quản lý version database MySQL
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Đọc .env, Settings class
│   │   │   ├── mysql.py
│   │   │   ├── mongodb.py
│   │   │   ├── redis.py
│   │   │   └── security.py     # JWT Auth
│   │   ├── models/
│   │   │   ├── sql/             # Bảng MySQL (SQLAlchemy)
│   │   │   └── nosql/           # Schema mapping cho MongoDB
│   │   ├── schemas/             # Pydantic DTOs
│   │   ├── services/
│   │   │   ├── document/
│   │   │   │   ├── parser.py
│   │   │   │   ├── classifier.py
│   │   │   │   └── embedding.py
│   │   │   ├── ai/
│   │   │   │   ├── summarizer.py
│   │   │   │   ├── quiz_generator.py
│   │   │   │   ├── grader.py
│   │   │   │   ├── rag.py
│   │   │   │   └── agent.py
│   │   │   └── sync_service.py
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── summary.py
│   │   │   │   ├── quiz.py
│   │   │   │   ├── grading.py
│   │   │   │   ├── qa.py
│   │   │   │   └── stats.py
│   │   │   └── ws/               # WebSocket & SSE endpoints
│   │   ├── utils/
│   │   └── main.py
│   ├── nginx/
│   ├── alembic.ini
│   ├── docker-compose.yml
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   ├── .env.example
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── (auth)/
    │   │   │   ├── login/page.tsx
    │   │   │   └── register/page.tsx
    │   │   ├── (dashboard)/
    │   │   │   ├── dashboard/page.tsx
    │   │   │   ├── documents/
    │   │   │   │   ├── [id]/page.tsx
    │   │   │   │   └── page.tsx
    │   │   │   ├── quizzes/
    │   │   │   │   ├── page.tsx
    │   │   │   │   └── [id]/
    │   │   │   │       ├── page.tsx
    │   │   │   │       └── result/page.tsx
    │   │   │   └── chat/page.tsx
    │   │   ├── layout.tsx
    │   │   └── globals.css
    │   ├── components/
    │   │   ├── ui/
    │   │   ├── layout/
    │   │   └── features/
    │   │       ├── auth/
    │   │       ├── document/
    │   │       ├── quiz/
    │   │       ├── chat/
    │   │       └── charts/
    │   ├── hooks/
    │   ├── services/
    │   ├── store/
    │   ├── types/
    │   ├── constants/
    │   └── utils/
    ├── .env.local
    ├── middleware.ts
    ├── tailwind.config.ts
    └── next.config.ts
```