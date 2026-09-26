#!/bin/sh
# Run migrations, then start the API. Single instance on purpose (see docs/threat-model.md T22).
set -eu
alembic -c /app/api/alembic.ini upgrade head
exec uvicorn --factory luibui_api.main:create_app --host 0.0.0.0 --port 8000 --no-server-header
