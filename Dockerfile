FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache \
    HOME=/home/ip-lens \
    API_BASE_URL=http://127.0.0.1:8001 \
    CHROMA_PATH=/app/data/chroma \
    DEMO_MODE=true

WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN useradd --create-home --uid 10001 ip-lens \
    && mkdir -p /app/data /home/ip-lens/.cache \
    && chown -R ip-lens:ip-lens /app /home/ip-lens

USER ip-lens
RUN uv run --no-sync python -c \
    "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()(['IP Lens embedding model warmup'])"

EXPOSE 7860
CMD ["bash", "deploy/start.sh"]
