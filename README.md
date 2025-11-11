# Chatbot RHM API

Medical chatbot API with RAG (Retrieval Augmented Generation) using Qdrant vector database.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Make (optional, for using Makefile commands)

## Quick Start

### Option 1: Run Locally

```bash
# Copy local environment config
copy .env.local .env

# Install dependencies
pip install -r requirements.txt

# Start local Qdrant (if not running)
docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Load vectors to Qdrant
python loadvector_qdrant.py

# Start API server
python start_api.py
```

API will be available at `http://localhost:8000`

### Option 2: Run with Docker 

```bash
# Copy docker environment config
copy .env.docker .env

# Build and start all services
docker-compose up --build -d

# Wait for services to be healthy (~10 seconds)
timeout /t 10 /nobreak

# Load vectors to Qdrant
python loadvector_qdrant.py

# Check status
docker-compose ps
```

### Option 3: Using Makefile (Recommended)

```bash
# Run locally
make local

# Build and run Docker (first time)
make docker-build

# Start Docker (already built)
make docker-up

# Stop Docker
make docker-down

# Load vectors only
make load-vectors

# Clean everything
make clean
```

## Environment Configuration

- `.env.local` - Local development (uses `localhost:6333` for Qdrant)
- `.env.docker` - Docker deployment (uses `qdrant:6333` service name)

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/chat` - Chat with the medical assistant

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI application |
| PostgreSQL | 5433 (local) / 5432 (docker) | Database |
| Qdrant | 6333 | Vector database |

## Development

```bash
# View logs
docker-compose logs -f chatbot-rhm-api

# Restart a service
docker-compose restart chatbot-rhm-api

# Rebuild after code changes
docker-compose up --build -d
```

## Troubleshooting

**Cannot connect to Qdrant in Docker:**
- Ensure `QDRANT_URL=http://qdrant:6333` in `.env`
- Check all services are healthy: `docker-compose ps`

**Vectors not loading:**
- Make sure Qdrant is running before loading vectors
- Check CSV files exist in `medical_knowledge_base/` directory

## Architecture

This project implements a multi-agent medical consultation system using PocketFlow. For detailed information about the system architecture and agent flow design, see:

- **[Design Document](docs/design.md)** - Complete flow design, node specifications, and implementation details

Key features:
- Multi-agent collaboration with specialized nodes (TopicClassifyAgent, RagAgent, FilterAgent)
- Reusable retrieve sub-flow for knowledge base queries
- Advanced RAG (Retrieval Augmented Generation) with filtering and ranking
- Graceful degradation with fallback mechanisms
- DEMUC topic classification (Diabetes, Endocrine, Metabolism, Urology, Cardiovascular)

## Project Structure

```
chatbot-rhm-api/
├── api/                    # API endpoints
├── core/                   # Core business logic (PocketFlow nodes & flows)
│   ├── flows/             # Multi-agent flows
│   └── nodes/             # Specialized agent nodes
├── utils/                  # Utilities (Qdrant, prompts, etc.)
├── medical_knowledge_base/ # CSV data files
├── database/               # Database migrations
├── docs/                   # Documentation
│   └── design.md          # System architecture & flow design
├── loadvector_qdrant.py    # Vector loading script
├── start_api.py            # API server entry point
├── docker-compose.yml      # Docker services configuration
└── Makefile               # Build automation
```
