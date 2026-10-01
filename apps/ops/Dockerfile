# syntax=docker/dockerfile:1.7
# Build context: repository root. pg_dump/pg_restore must be at least the server's version (17),
# so the image starts from the same postgres:17 image the database runs on; Python, psycopg and
# age come from Debian. No pip, no venv: luibui_ops uses only the standard library and psycopg.
FROM postgres:17-trixie
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-psycopg age tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10002 --no-create-home --home-dir /nonexistent luibui \
 && mkdir -p /backup && chown 10002:10002 /backup && chmod 700 /backup
COPY apps/ops/luibui_ops /app/luibui_ops
ARG LUIBUI_VERSION=lokal
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BACKUP_DIR=/backup \
    LUIBUI_VERSION=${LUIBUI_VERSION}
USER 10002
WORKDIR /tmp
ENTRYPOINT ["python3", "-m", "luibui_ops"]
