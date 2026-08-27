FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY api ./api
COPY models ./models
COPY tools ./tools
COPY term_mcp_deepseek ./term_mcp_deepseek
COPY config.py mcp_server.py server.py stdio_server.py ./
RUN python -m pip install --no-cache-dir .

COPY static ./static

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://127.0.0.1:8000/health || exit 1

CMD ["python", "-m", "term_mcp_deepseek", "serve", "--host", "0.0.0.0", "--port", "8000"]
