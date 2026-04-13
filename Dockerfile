FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.1.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    sentence-transformers==3.0.0 \
    --no-deps

COPY requirements-api.txt .
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements-api.txt

COPY cre/ ./cre/
COPY api/ ./api/

EXPOSE 8000
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
