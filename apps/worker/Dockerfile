# syntax=docker/dockerfile:1.7
# Build context: repository root. Scanners (gitleaks, osv-scanner, …) are added in Sprint 1,
# pinned with checksums (docs/scanner-tools.md).

FROM python:3.12-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages packages
COPY apps/api apps/api
COPY apps/worker apps/worker
RUN uv sync --frozen --no-dev --no-editable --package luibui-worker

FROM python:3.12-slim-trixie
RUN useradd --system --uid 10001 --no-create-home --home-dir /nonexistent luibui \
 && mkdir -p /scratch /rules && chown 10001:10001 /scratch && chmod 700 /scratch
COPY --from=build /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SCRATCH_ROOT=/scratch LITELLM_LOCAL_MODEL_COST_MAP=True
USER 10001
WORKDIR /scratch
ENTRYPOINT ["luibui-worker"]
