FROM python:3.11-slim

WORKDIR /app

# System deps for ChromaDB + sentence-transformers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install CRE core + API deps
COPY pyproject.toml .
COPY requirements-api.txt .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements-api.txt

# Copy source
COPY cre/ ./cre/
COPY api/ ./api/

# Railway sets PORT env var automatically
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
