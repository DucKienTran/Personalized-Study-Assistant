# LearningAId: AI Learning Assistant

> Hệ thống hỗ trợ học tập thông minh, cho phép người dùng tải lên tài liệu bài giảng để AI tự động xử lý nội dung.

**Lưu ý:** Hệ thống chỉ có 1 role duy nhất, không phân chia giáo viên hay học sinh — người dùng có thể vừa tạo đề, vừa tự làm bài, vừa tự chấm.

## 1. Mô tả

Người dùng tổ chức tài liệu theo **Notebook** — mỗi notebook là một nhóm tài liệu thuộc cùng một chủ đề/môn học, và mọi tính năng AI (tóm tắt, tạo đề, hỏi đáp, lịch sử) đều thao tác trong phạm vi một notebook.

### Chức năng chính

- Tóm tắt tài liệu học tập
- Tạo bài kiểm tra từ nội dung tài liệu, với nhiều dạng câu hỏi (Multiple Choice, Multiple Select, True/False, Fill in the Blank, Short Answer, Essay) và 2 chế độ: **Study mode** (làm tự do, xem giải thích ngay) và **Exam mode** (làm có giới hạn thời gian, chấm sau khi nộp)
- Hệ thống tự động điều chỉnh độ khó/phong cách đề theo phản hồi cá nhân của từng người dùng qua thời gian (adaptive quiz profile)
- Chấm điểm và đánh giá kết quả bài kiểm tra (tự động với câu hỏi khách quan, AI chấm theo rubric với tự luận)
- Hỏi đáp trực tiếp dựa trên tài liệu đã tải lên (RAG), có trích dẫn nguồn và nhảy trực tiếp đến vị trí trong PDF
- Tính năng "Explain" ngay trong lúc làm/xem lại bài: từ một câu hỏi kiểm tra, hỏi thêm AI để giải thích sâu hơn, tự động chuyển sang tab Hỏi đáp
- Thống kê hoạt động học tập: biểu đồ độ chính xác theo dạng câu hỏi, tiến độ theo thời gian

### Input

- Giáo trình, slide bài giảng (PDF, DOCX)
- Tài liệu dạng văn bản thuần (TXT, Markdown), có thể dán trực tiếp thay vì upload file
- Bài làm độc lập upload lên để đối chiếu chấm điểm

### Output

- Nội dung tóm tắt
- Bộ câu hỏi kiểm tra (export PDF/DOCX)
- Kết quả chấm điểm, kèm giải thích theo từng lựa chọn
- Câu trả lời cho các câu hỏi liên quan đến tài liệu, kèm trích dẫn

## 2. Cấu trúc thư mục

```
learning-aid/
├── backend/
│   ├── alembic/                 # Quản lý version database MySQL
│   ├── app/
│   │   ├── ai/
│   │   │   ├── constants/
│   │   │   │   └── quiz_profile.py        # Default profile, bounds, semantics
│   │   │   ├── embeddings/
│   │   │   │   ├── base.py
│   │   │   │   └── voyage_client.py
│   │   │   ├── llm/
│   │   │   │   ├── azure_openai_client.py
│   │   │   │   ├── base.py
│   │   │   │   └── gemini_client.py
│   │   │   ├── output/                     # Parser/output cho kết quả AI trả về
│   │   │   │   ├── classifier_output.py
│   │   │   │   ├── classifier_parser.py
│   │   │   │   └── quiz_parser.py
│   │   │   └── prompts/
│   │   │       ├── classifier_prompt.py
│   │   │       ├── dashboard_insight_prompt.py
│   │   │       ├── feedback_analyzer_prompt.py
│   │   │       ├── quiz_instruction_prompt.py
│   │   │       ├── quiz_prompt.py
│   │   │       ├── rag_prompt.py
│   │   │       └── summary_prompt.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── conversation.py
│   │   │   ├── dashboard.py
│   │   │   ├── documents.py
│   │   │   ├── notebooks.py
│   │   │   ├── quizzes.py
│   │   │   ├── rag.py
│   │   │   ├── summaries.py
│   │   │   └── users.py
│   │   ├── core/
│   │   │   ├── config.py        # Đọc .env, Settings class
│   │   │   ├── database.py
│   │   │   ├── dependencies.py
│   │   │   ├── logging.py
│   │   │   └── security.py      # JWT Auth
│   │   ├── models/                          # SQLAlchemy models (MySQL), phẳng, không tách sql/nosql
│   │   │   ├── conversation_model.py
│   │   │   ├── dashboard_insight_model.py
│   │   │   ├── document_model.py
│   │   │   ├── notebook_model.py
│   │   │   ├── quiz_model.py
│   │   │   ├── quiz_offset_model.py
│   │   │   └── user_model.py
│   │   ├── schemas/                         # Pydantic DTOs
│   │   │   ├── conversation_schema.py
│   │   │   ├── dashboard_schema.py
│   │   │   ├── document_schema.py
│   │   │   ├── notebook_schema.py
│   │   │   ├── quiz_profile_schema.py
│   │   │   ├── quiz_schema.py
│   │   │   ├── rag_schema.py
│   │   │   ├── response_schema.py
│   │   │   ├── summary_schema.py
│   │   │   ├── token_schema.py
│   │   │   └── user_schema.py
│   │   ├── services/
│   │   │   ├── dashboard/                  # dashboard_service.py + dashboard_insight_service.py
│   │   │   ├── document/
│   │   │   │   ├── chunk_builder.py
│   │   │   │   ├── classifier_service.py
│   │   │   │   ├── cleaner.py
│   │   │   │   ├── constants.py
│   │   │   │   ├── document_processing_service.py
│   │   │   │   ├── document_service.py
│   │   │   │   ├── embedding_service.py
│   │   │   │   ├── metadata_builder.py
│   │   │   │   ├── models.py
│   │   │   │   ├── parser.py
│   │   │   │   └── pipeline.py
│   │   │   ├── notebook/
│   │   │   │   └── notebook_service.py
│   │   │   ├── quiz/
│   │   │   │   ├── chunk_selector.py
│   │   │   │   ├── feedback_service.py
│   │   │   │   ├── instruction_parser.py
│   │   │   │   ├── personal_offset_service.py
│   │   │   │   ├── quiz_pipeline.py
│   │   │   │   └── quiz_service.py
│   │   │   ├── rag/
│   │   │   │   ├── conversation_service.py
│   │   │   │   ├── evaluation_trace.py
│   │   │   │   ├── rag_service.py
│   │   │   │   ├── retrieval_models.py
│   │   │   │   └── retrieval_service.py
│   │   │   ├── summary/
│   │   │   │   ├── models.py
│   │   │   │   ├── summary_record_service.py
│   │   │   │   ├── summary_service.py
│   │   │   │   └── token_batcher.py
│   │   │   ├── auth_service.py
│   │   │   ├── email_service.py
│   │   │   ├── presence_service.py
│   │   │   ├── token_service.py
│   │   │   └── user_service.py
│   │   ├── storage/
│   │   │   ├── base.py
│   │   │   └── minio_storage.py            # Lưu file gốc (PDF/DOCX...) trên MinIO
│   │   ├── utils/
│   │   │   ├── file_handler.py
│   │   │   └── response.py
│   │   └── main.py
│   ├── chroma_data/ / chroma_storage/       # Chroma persist cục bộ (embedded, không phải server riêng)
│   ├── evaluation/                          # Đánh giá chất lượng RAG/quiz
│   ├── scripts/
│   ├── tests/
│   ├── nginx/                     # reverse proxy, trung gian phục vụ file PDF qua MinIO presigned URL
│   ├── alembic.ini
│   ├── docker-compose.yml
│   ├── Dockerfile.dev
│   ├── Dockerfile.prod
│   ├── .env.dev / .env.example
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── (auth)/
    │   │   │   ├── change-password/
    │   │   │   ├── forgot-password/
    │   │   │   ├── login/
    │   │   │   ├── register/
    │   │   │   ├── reset-password/
    │   │   │   └── verify-email/
    │   │   ├── (workspace)/
    │   │   │   ├── dashboard/                 # Thống kê chi tiết (biểu đồ)
    │   │   │   ├── documents/
    │   │   │   │   └── [id]/page.tsx          # Xem chi tiết 1 tài liệu
    │   │   │   ├── notebooks/
    │   │   │   │   ├── [id]/page.tsx          # Chi tiết notebook: tabs Assistant / Summary / Quizzes / History
    │   │   │   │   └── page.tsx               # Danh sách notebook
    │   │   │   ├── quizzes/
    │   │   │   │   └── [id]/
    │   │   │   │       ├── exam/              # Trang làm bài Exam mode (route riêng, tách biệt khỏi tab)
    │   │   │   │       ├── layout.tsx
    │   │   │   │       └── page.tsx
    │   │   │   └── layout.tsx
    │   │   ├── layout.tsx
    │   │   └── globals.css
    │   ├── components/                # domain folder phẳng, không gộp vào 1 features/ chung
    │   │   ├── auth/
    │   │   ├── chat/                  # Assistant tab (RAG chat + trích dẫn)
    │   │   ├── dashboard/
    │   │   ├── document-viewer/       # PDF/DOCX/TXT/MD viewer
    │   │   ├── documents/
    │   │   ├── features/
    │   │   ├── layout/
    │   │   ├── notebooks/
    │   │   ├── pdf-viewer/
    │   │   ├── quizzes/
    │   │   ├── shared/
    │   │   ├── states/
    │   │   └── ui/                    # component nền tảng theo phong cách shadcn/ui trên Base UI
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

## 3. Luồng sử dụng

**Bước 1 — Đăng nhập**
Người dùng đăng nhập vào hệ thống bằng JWT Auth.

**Bước 2 — Tạo/chọn Notebook**
Người dùng tạo một notebook (tiêu đề, mô tả, màu tag) hoặc chọn notebook có sẵn để làm việc.

**Bước 3 — Upload tài liệu**
Trong một notebook, người dùng tải lên file (PDF, DOCX, TXT, Markdown) hoặc dán trực tiếp văn bản, gán nhãn thủ công:
- Loại tài liệu: giáo trình/tài liệu học tập, đề mẫu/đáp án, hoặc tài liệu tham khảo bổ sung.
- Môn học: hệ thống gợi ý dựa trên tên file và nội dung trang đầu, người dùng xác nhận hoặc sửa lại.

Trong lúc xử lý (parse/embedding), tài liệu hiển thị trạng thái loading trong sidebar và tạm thời bị vô hiệu hoá tương tác. File gốc được lưu trên MinIO, phục vụ qua Nginx reverse proxy bằng presigned URL.

**Bước 4 — Trích xuất nội dung** (chạy một lần sau khi upload)
Hệ thống parse file, trích xuất toàn bộ text, hình ảnh, cấu trúc trang.

**Bước 5 — Phân loại tài liệu**
Hệ thống tự động phân tích:
- Mục đích tài liệu: khai thác nội dung để học hay chỉ tham khảo cấu trúc/form.
- Tài liệu có đủ kiến thức để sinh câu hỏi tự luận không.
- Tài liệu có chứa hình ảnh có ý nghĩa học tập không, phân biệt hình minh họa và hình chứa kiến thức.

Kết quả phân loại quyết định module nào được unlock ở bước tiếp theo.

**Bước 6 — Tạo embedding và lưu vào database**
Nội dung text và hình ảnh có ý nghĩa được tạo vector embedding (Voyage), lưu vào Chroma (persist cục bộ) phục vụ RAG. Nội dung trích xuất, bản tóm tắt, lịch sử chat lưu ở MongoDB; metadata lưu ở MySQL.

**Bước 7 — Người dùng chọn chức năng** (thao tác qua các tab trong trang chi tiết notebook)

- **7.1 Tóm tắt tài liệu** — AI tóm tắt nội dung theo chủ đề, lưu kết quả, hiển thị lên web.
- **7.2 Kiểm tra** — AI sinh bộ câu hỏi và đáp án mẫu, có thể export PDF/DOCX. Người dùng cấu hình số câu, độ khó, hướng dẫn cá nhân, và chọn Study mode hoặc Exam mode (giới hạn thời gian, đánh dấu câu hỏi cần xem lại/quan trọng). Hệ thống tự điều chỉnh độ khó theo phản hồi (tag preset + bình luận tự do) mà người dùng để lại sau mỗi lần làm bài.
- **7.3 Chấm bài** — chấm tự động với câu hỏi khách quan, AI chấm theo rubric với tự luận, hoặc đối chiếu bài làm upload độc lập với tài liệu gốc.
- **7.4 Hỏi đáp theo tài liệu** — chat hỏi đáp dựa trên RAG (hybrid vector + BM25, có rerank), AI trả lời kèm trích dẫn nội dung liên quan, nhảy trực tiếp đến vị trí trong PDF. Có thể mở từ một câu hỏi kiểm tra (tính năng Explain) để hỏi sâu hơn về kiến thức liên quan.

**Bước 8 — Thống kê kết quả**
Tổng hợp hoạt động người dùng: lịch sử hỏi đáp, tài liệu đã tóm tắt, điểm số và lịch sử làm bài (History tab trong notebook). Trang Thống kê tổng (Dashboard) hiển thị biểu đồ độ chính xác theo dạng câu hỏi và tiến độ học tập, cập nhật realtime qua WebSocket/SSE.

**Hệ thống nền** (chạy xuyên suốt)
Redis cache kết quả và session, LangChain/Mastra Agent điều phối tác vụ AI, MinIO lưu trữ file gốc, Docker và Nginx triển khai hệ thống, CI/CD quản lý log và deploy.

### Database

| Database | Vai trò |
|----------|---------|
| **MySQL** | Tài khoản, notebook, thông tin file, đề kiểm tra, kết quả chấm điểm, hồ sơ điều chỉnh cá nhân (quiz profile offset) |
| **MongoDB** | Nội dung trích xuất từ tài liệu, bản tóm tắt, lịch sử chat, dữ liệu sync lưu trữ dài hạn |
| **Chroma** | Vector embedding phục vụ truy hồi RAG (persist cục bộ trong `chroma_data/`, `chroma_storage/`) |
| **Redis** | Cache JWT/blacklist token, cache kết quả AI, hỗ trợ truyền dữ liệu realtime (WebSocket/SSE) |
| **MinIO** | Lưu trữ file gốc đã upload (PDF, DOCX...) |

## 4. ERD MySQL

```
users (1) ──────< (n) notebooks ──────< (n) documents
  │                      │                      │
  │                      ├──< (n) quizzes        │
  │                      │        │              │
  │                      │        └──< (n) quiz_questions
  │                      │        └──< (n) quiz_attempts
  │                      │                      │
  │                      └──< (n) conversations  │
  │                                              │
  └──< (n) user_quiz_profile_offsets            │
```

## 5. Công nghệ sử dụng

- **Backend:** FastAPI (Python 3.12), SQLAlchemy + Alembic; LLM: Gemini, Azure OpenAI; Embedding: Voyage; Vector DB: Chroma; Object storage: MinIO
- **Frontend:** Next.js 15 (App Router) + React 19, TypeScript, Tailwind CSS, component nền Base UI theo phong cách shadcn/ui, React Hook Form + Zod, Framer Motion
- **Hạ tầng:** Docker Compose, Nginx (reverse proxy, phục vụ PDF qua MinIO presigned URL)