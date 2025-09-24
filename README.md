# Chatbot RHM API - Hướng dẫn cho người mới

> 🎯 **Mục tiêu**: Giúp người mới hiểu và làm việc với codebase ngay lập tức không cần giải thích thêm

## 📋 Tổng quan dự án

Đây là một **hệ thống chatbot y khoa** sử dụng AI để tư vấn về bệnh răng - hàm - mặt và đái tháo đường. Hệ thống được xây dựng trên:

- **PocketFlow**: Framework xử lý luồng AI workflow
- **FastAPI**: API backend 
- **PostgreSQL**: Database lưu trữ users, threads, messages
- **Gemini AI**: LLM engine để xử lý câu hỏi
- **TF-IDF + Vector Search**: Tìm kiếm trong knowledge base

### 🎭 Các vai trò người dùng để set field role cho route /chat tương ứng

1. **Bệnh nhân nha khoa** (`patient_dental`)
2. **Bệnh nhân đái tháo đường** (`patient_diabetes`) 
3. **Bác sĩ nha khoa** (`doctor_dental`)
4. **Bác sĩ nội tiết** (`doctor_endocrine`)
5. **Bác sĩ chỉnh nha** (`orthodontist`)  <- dùng cho cái web, 3 cái trên dùng cho app 


## 📋 Yêu cầu hệ thống

### Phiên bản được hỗ trợ
- **Python**: 3.11+ (khuyến nghị 3.11)
- **PostgreSQL**: 15+
- **Docker**: 20.10+ và Docker Compose v2
- **Node.js**: 16+ (nếu cần frontend integration)

### Cấu hình tối thiểu
- **RAM**: 2GB+ (khuyến nghị 4GB)
- **Storage**: 5GB+ trống
- **CPU**: 2 cores+

## 🚀 Chạy bằng Docker (khuyến nghị cho production)

> 🎯 **Tốt nhất cho**: Deploy production, frontend developers, team collaboration

### 1) Chuẩn bị môi trường

#### Cài đặt Docker


#### Kiểm tra cài đặt
```bash
docker --version
docker-compose --version
```

- Tạo file `.env` tại thư mục gốc:

```
API_HOST=0.0.0.0
API_PORT=8000
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=chatbot
POSTGRES_PORT=5432
GEMINI_API_KEY=your_gemini_key
GEMINI_API_KEYS=key1,key2,..
```

### 2) Khởi chạy backend API + Postgres

```bash
# Khởi chạy tất cả services
docker compose up -d --build

# Kiểm tra status các containers
docker compose ps

# Xem logs real-time
docker compose logs -f chatbot-rhm-api
```

**Quá trình khởi động:**
1. PostgreSQL container khởi động và chạy health check
2. API container đợi DB healthy rồi mới start
3. API sẽ tự động tạo tables và sẵn sàng tại `http://localhost:8000`

### 2.1) Quản lý Docker containers

```bash
# Xem status
docker compose ps

# Restart một service
docker compose restart chatbot-rhm-api

# Rebuild khi có thay đổi code
docker compose up -d --build chatbot-rhm-api

# Dừng tất cả
docker compose down

# Dừng và xóa volumes (⚠️ mất data)
docker compose down -v
```

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

### 5) Debugging Docker

```bash
# Xem logs của service cụ thể
docker compose logs chatbot-rhm-api
docker compose logs postgres

# Truy cập vào container đang chạy
docker compose exec chatbot-rhm-api bash
docker compose exec postgres psql -U postgres -d chatbot

# Xem thông tin chi tiết container
docker compose exec chatbot-rhm-api python -c "import sys; print(sys.version)"

# Kiểm tra network connectivity
docker compose exec chatbot-rhm-api ping postgres
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

### 2. Cấu hình environment variables

Tạo file `.env`:

```env
# Database (điều chỉnh theo cấu hình local)
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/chatbot

# Gemini AI (bắt buộc)
GEMINI_API_KEY=your_gemini_api_key_here
# Hoặc nhiều keys để tăng quota:
GEMINI_API_KEYS=key1,key2,key3

# Google OAuth (tuỳ chọn)
GOOGLE_CLIENT_ID=your_google_client_id

# JWT Security (tạo secret key mạnh)
SECRET_KEY=your_very_long_random_secret_key_here

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true  # Chỉ trong development
```

### 5. Kiểm tra kết nối database

```bash
# Test connection
python -c "
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
print('✅ Database connection successful')
conn.close()
"
```



### 7. Truy cập API Documentation

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
