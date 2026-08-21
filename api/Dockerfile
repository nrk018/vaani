FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt faiss-cpu

COPY api/app /app/app
COPY ingest /app/ingest
COPY knowledge /app/knowledge
COPY eval /app/eval
COPY data /app/data

ENV PYTHONPATH=/app
ENV INDEX_DIR=/app/data/index
ENV VAANI_HASH_EMBEDDINGS=1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
