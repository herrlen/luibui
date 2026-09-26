# syntax=docker/dockerfile:1.7
# Build context: repository root.

FROM python:3.12-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages packages
COPY apps/api apps/api
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --no-editable --package luibui-api

FROM python:3.12-slim-trixie
RUN useradd --system --uid 10001 --no-create-home --home-dir /nonexistent luibui \
 && mkdir -p /projects && chown 10001:10001 /projects
COPY --from=build /app/.venv /app/.venv
COPY apps/api/alembic.ini /app/api/alembic.ini
COPY apps/api/alembic /app/api/alembic
COPY --chmod=755 apps/api/docker-entrypoint.sh /app/docker-entrypoint.sh
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]
ENTRYPOINT ["/app/docker-entrypoint.sh"]
