# Use Python 3.11 slim base image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FASTEMBED_CACHE_PATH=/app/models

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create cache directory for models
RUN mkdir -p /app/models

# Pre-download embedding models to cache them in Docker image
# This prevents re-downloading models on every container startup
RUN python -c "from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding; \
    TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/models'); \
    print('📥 Downloading sparse model...'); \
    SparseTextEmbedding('Qdrant/bm25', cache_dir='/app/models'); \
    print('📥 Downloading late interaction model...'); \
    LateInteractionTextEmbedding('colbert-ir/colbertv2.0', cache_dir='/app/models'); \
    print('✅ All models cached successfully!')"

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/logs \
    && chown -R app:app /app \
    && chmod -R 755 /app/logs \
    && chmod -R 755 /app/models
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command to run the application
CMD ["python", "start_api.py"]
