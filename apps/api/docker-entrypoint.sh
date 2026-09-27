#!/bin/sh
# Run migrations, then start the API. Single instance on purpose (see docs/threat-model.md T22).
#
# Client IP: uvicorn takes it from X-Forwarded-For only if the direct peer is in FORWARDED_ALLOW_IPS
# (on mittwald the cluster network 100.121.0.0/16: ingress and our own containers). The access log is
# off by default, because with real client IPs it would hold personal data (ENTWICKLERREGELN A11);
# LUIBUI_ACCESS_LOG=1 switches it on for a short check.
set -eu
alembic -c /app/api/alembic.ini upgrade head
ACCESS_LOG="--no-access-log"
[ "${LUIBUI_ACCESS_LOG:-0}" = "1" ] && ACCESS_LOG="--access-log"
exec uvicorn --factory luibui_api.main:create_app --host 0.0.0.0 --port 8000 --no-server-header \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" "$ACCESS_LOG"
