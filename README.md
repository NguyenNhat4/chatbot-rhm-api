# Chatbot RHM API - Hướng dẫn cho người mới

> 🎯 **Mục tiêu**: Giúp người mới hiểu và làm việc với codebase ngay lập tức không cần giải thích thêm

## 📋 Tổng quan dự án

Đây là một **hệ thống chatbot y khoa** sử dụng AI để tư vấn về bệnh răng - hàm - mặt và đái tháo đường. Hệ thống được xây dựng trên:

- **PocketFlow**: Framework xử lý luồng AI workflow
- **FastAPI**: API backend 
- **PostgreSQL**: Database lưu trữ users, threads, messages
- **Gemini AI**: LLM engine để xử lý câu hỏi
- **TF-IDF + Vector Search**: Tìm kiếm trong knowledge base

### 🎭 Các vai trò người dùng

1. **Bệnh nhân nha khoa** (`patient_dental`)
2. **Bệnh nhân đái tháo đường** (`patient_diabetes`) 
3. **Bác sĩ nha khoa** (`doctor_dental`)
4. **Bác sĩ nội tiết** (`doctor_endocrine`)

## 🚀 Chạy bằng Docker (dành cho frontend dev)

### 1) Chuẩn bị môi trường

- Cài Docker và Docker Compose
- Tạo file `.env` tại thư mục gốc, ví dụ:

```
API_HOST=0.0.0.0
API_PORT=8000
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=chatbot
POSTGRES_PORT=5432
GEMINI_API_KEY=your_gemini_key
```

### 2) Khởi chạy backend API + Postgres

```bash
docker compose up -d --build
```

Đợi Postgres healthy, API sẽ tự start tại `http://localhost:8000`.

### 3) Kiểm tra nhanh

- Health: `http://localhost:8000/api/health`
- Swagger: `http://localhost:8000/api/docs`

### 4) Gọi API từ frontend

- Endpoint chat: `POST /api/chat`
- Body JSON:

```json
{
  "message": "em bị ê buốt răng",
  "role": "patient_dental",
  "session_id": "<thread_id do FE quản lý>"
}
```

Lưu ý:
- Trước khi gọi chat cần tạo `thread` (session_id) bên phía DB của hệ thống (API hiện chỉ nhận `session_id` đã tồn tại và thuộc user).
- Header Authorization: Bearer <token> (sau khi login qua `/api/auth/login` hoặc `/api/auth/token`).

### 5) Dừng và xem logs

```bash
docker compose logs -f chatbot-rhm-api
docker compose down
```

---

## 🏗️ Kiến trúc hệ thống (tóm tắt)

```mermaid
flowchart TD
    A[IngestQuery] --> B[MainDecisionAgent]
    B -->|medical_question| C[RetrieveFromKB]
    B -->|fallback| D[FallbackNode]
    C --> F[ScoreDecisionNode]
    F -->|score >= threshold| G[ComposeAnswer]
    F -->|score < threshold| H[ClarifyQuestionNode]
    G -->|API overload| D
    B -->|chitchat| I[ChitChatRespond]
```

### Cấu trúc thư mục

```
chatbot-rhm-api/
├── 📁 database/           # Database models & connection
│   ├── db.py             # Database setup
│   ├── models.py         # SQLAlchemy models  
│   └── init.sql          # Database schema
├── 📁 utils/             # Utility functions
│   ├── call_llm.py       # Gemini AI integration
│   ├── kb.py             # Knowledge base search
│   ├── prompts.py        # LLM prompts
│   ├── role_enum.py      # User roles definition
│   └── response_parser.py # YAML response parsing
├── 📁 services/          # Business logic
│   └── chat_service.py   # Chat operations
├── 📁 schemas/           # Pydantic schemas  
│   └── chat_schemas.py   # API request/response models
├── 📁 routes/            # API routes (deprecated)
├── 📁 medical_knowledge_base/ # CSV knowledge files
│   ├── bndtd.csv         # Bệnh nhân đái tháo đường
│   ├── bnrhm.csv         # Bệnh nhân răng hàm mặt
│   ├── bsnt.csv          # Bác sĩ nội tiết
│   └── bsrhm.csv         # Bác sĩ răng hàm mặt
├── api.py                # Main API server
├── flow.py               # PocketFlow definition
├── nodes.py              # Flow nodes implementation
├── chat_routes.py        # Chat thread management routes
├── config.py             # Configuration settings
└── main.py               # Entry point
```

## 🚀 Cài đặt và chạy dự án

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình environment variables

Tạo file `.env`:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
# Hoặc nhiều keys cách nhau bằng dấu phẩy:
GEMINI_API_KEYS=key1,key2,key3

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id

# JWT Security
SECRET_KEY=your_secret_key_here

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

### 3. Setup database

```bash
# Tạo database PostgreSQL trước
# Sau đó tables sẽ được tạo tự động khi chạy API
```

### 4. Chạy API server

```bash
# Development mode
python api.py

# Hoặc với uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Truy cập API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 Các thành phần chính

### 1. API Endpoints (api.py)

#### Authentication
- `POST /api/auth/login` - Đăng nhập email/password
- `POST /api/auth/google` - Đăng nhập Google OAuth
- `POST /api/users` - Tạo tài khoản mới

#### Chat API
- `POST /api/chat` - Gửi tin nhắn chat chính
- `GET /api/roles` - Lấy danh sách roles

#### Thread Management (chat_routes.py)
- `GET /api/threads/` - Lấy danh sách threads
- `POST /api/threads/` - Tạo thread mới
- `GET /api/threads/{id}` - Lấy thread + messages
- `PUT /api/threads/{id}/rename` - Đổi tên thread
- `DELETE /api/threads/{id}` - Xóa thread

### 2. PocketFlow Workflow (flow.py + nodes.py)

#### Các Nodes chính:

1. **IngestQuery**: Xử lý input từ user
2. **MainDecisionAgent**: Phân loại intent (greeting/medical_question/chitchat/topic_suggestion)
3. **RetrieveFromKB**: Tìm kiếm trong knowledge base
4. **ScoreDecisionNode**: Quyết định dựa trên relevance score
5. **ComposeAnswer**: Tạo câu trả lời bằng LLM
6. **ClarifyQuestionNode**: Xử lý khi score thấp
7. **GreetingResponse**: Trả lời chào hỏi
8. **FallbackNode**: Xử lý khi API quá tải

### 3. Knowledge Base (utils/kb.py)

- **TF-IDF Vector Search** trên 4 file CSV theo role
- **Role-specific search**: Mỗi role tìm trong CSV riêng
- **Fallback search**: Tìm trong tất cả data nếu không có role-specific
- **Random suggestions**: Lấy câu hỏi ngẫu nhiên theo role

### 4. LLM Integration (utils/call_llm.py)

- **Multi-key management**: Tự động switch khi API overload
- **Automatic retry**: Thử lại với key khác khi quota exceeded
- **Token estimation**: Ước tính tokens cho logging
- **Error handling**: Graceful fallback khi all keys fail

## 📝 Quy trình phát triển

### 1. Thêm feature mới

#### Thêm API endpoint mới:
1. Tạo schema trong `schemas/chat_schemas.py`
2. Thêm business logic trong `services/chat_service.py`
3. Tạo endpoint trong `api.py` hoặc `chat_routes.py`

#### Thêm node mới vào flow:
1. Implement node class trong `nodes.py`
2. Kết nối node trong `flow.py`
3. Test với `flow.run(shared_data)`

### 2. Modify prompts

Chỉnh sửa trong `utils/prompts.py`:
- `PROMPT_CLASSIFY_INPUT`: Phân loại intent
- `PROMPT_COMPOSE_ANSWER`: Tạo câu trả lời

### 3. Thêm role mới

1. Thêm vào `utils/role_enum.py`:
   ```python
   class RoleEnum(str, Enum):
       NEW_ROLE = "new_role"
   ```

2. Thêm CSV file tương ứng vào `medical_knowledge_base/`

3. Cập nhật mapping trong `utils/kb.py`:
   ```python
   ROLE_TO_CSV = {
       RoleEnum.NEW_ROLE.value: "new_role.csv",
   }
   ```

### 4. Database migration

Khi thay đổi models trong `database/models.py`:
```bash
# Tạo migration
alembic revision --autogenerate -m "Add new field"

# Apply migration  
alembic upgrade head
```

## 🧪 Testing & Debugging

### 1. Test individual components

```python
# Test knowledge base
from utils.kb import retrieve
results, score = retrieve("đau răng", "patient_dental", top_k=3)

# Test LLM
from utils.call_llm import call_llm
response = call_llm("Hello, how are you?")

# Test flow
from flow import create_med_agent_flow
flow = create_med_agent_flow()
shared = {"role": "patient_dental", "input": "Tôi bị đau răng"}
flow.run(shared)
print(shared["explain"])
```

### 2. API Testing

```bash
# Test authentication
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "password"}'

# Test chat
curl -X POST "http://localhost:8000/api/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị đau răng", "role": "patient_dental", "session_id": "thread_id"}'
```

### 3. Debug logs

Logs được ghi chi tiết trong console. Quan trọng:
- `🔍 [IngestQuery]` - Input processing
- `📚 [RetrieveFromKB]` - Knowledge base search
- `✍️ [ComposeAnswer]` - LLM response generation
- `🤖 [call_llm]` - API calls

## ⚠️ Lưu ý quan trọng

### 1. API Rate Limits
- Gemini có quota limits, dùng multiple API keys
- Hệ thống tự động switch keys khi overload
- Fallback mode khi all keys fail

### 2. Security
- JWT tokens cho authentication  
- CORS configured cho cross-origin requests
- Password hashing với bcrypt
- Input validation với Pydantic

### 3. Performance
- Knowledge base được cache trong memory
- Role-specific search để tăng tốc
- Pagination cho thread messages
- Connection pooling cho database

### 4. Data format
- Knowledge base: CSV với columns chuẩn
- LLM responses: YAML format với validation
- Database: PostgreSQL với foreign keys

## 🆘 Troubleshooting thường gặp

### 1. API không start được
```bash
# Kiểm tra environment variables
python -c "import os; print(os.getenv('DATABASE_URL'))"

# Kiểm tra database connection
python check_db.py
```

### 2. Knowledge base không load
```bash
# Kiểm tra CSV files
ls -la medical_knowledge_base/

# Test knowledge base loading
python -c "from utils.kb import get_kb; kb = get_kb(); print(len(kb.df))"
```

### 3. LLM không trả lời
```bash
# Kiểm tra API keys
python -c "from utils.call_llm import get_api_key_status; print(get_api_key_status())"

# Test LLM directly
python utils/call_llm.py
```

### 4. Flow lỗi
```bash
# Test individual nodes
python -c "
from nodes import IngestQuery
from flow import create_med_agent_flow
shared = {'role': 'patient_dental', 'input': 'test'}
flow = create_med_agent_flow()
flow.run(shared)
print(shared)
"
```

## 📞 Hỗ trợ

Khi gặp vấn đề:
1. Kiểm tra logs trong console
2. Verify environment variables
3. Test individual components trước
4. Kiểm tra database connection
5. Confirm API keys còn quota

---

**Happy coding! 🚀**

> Tài liệu này đảm bảo bạn có thể hiểu và làm việc với codebase ngay lập tức. Nếu có thắc mắc gì, hãy đọc code trong các file tương ứng để hiểu chi tiết hơn.
