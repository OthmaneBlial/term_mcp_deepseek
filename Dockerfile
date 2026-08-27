# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
ARG PYTHON_IMAGE=python:3.12.14-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579

FROM ${PYTHON_IMAGE} AS wheel-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY . .
RUN python -m pip wheel --constraint constraints.txt --wheel-dir /wheels .

FROM ${PYTHON_IMAGE} AS runtime

ENV HOST=0.0.0.0 \
    PIP_ROOT_USER_ACTION=ignore \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKSPACE_ROOT=/workspace

RUN groupadd --gid 10001 termmcp \
    && useradd --uid 10001 --gid termmcp --create-home --shell /usr/sbin/nologin termmcp \
    && mkdir --parents /workspace \
    && chown termmcp:termmcp /workspace

COPY --from=wheel-builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels term-mcp-deepseek \
    && rm -rf /wheels

USER 10001:10001
WORKDIR /workspace

EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["term-mcp", "serve", "--host", "0.0.0.0", "--port", "8000"]
