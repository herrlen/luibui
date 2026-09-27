#!/usr/bin/env bash
# Local release with Docker Desktop instead of GitHub Actions: check, build, push, deploy.
#
#   scripts/release.sh                 alles: Prüfungen, Images, Push, Ausrollen
#   scripts/release.sh --ohne-deploy   nur prüfen, bauen und pushen
#
# Builds exactly the committed state (git archive HEAD), never the working tree. Secrets are read
# from the running mittwald stack and handed to `mw` in a mode-600 temp file that is deleted
# afterwards; nothing is printed. ANNAHME_OFFEN and SMTP_PASSWORD keep their deployed values
# unless set in the environment (ANNAHME_OFFEN=true scripts/release.sh).
#
# Needs: Docker Desktop (context desktop-linux), gh (token with write:packages), mw, jq, uv,
# pnpm. Optional for the full test set: LUIBUI_GITLEAKS, LUIBUI_OSV_SCANNER, LUIBUI_OSV_DB.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Docker Desktop's credential helper lives inside the app bundle.
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"
cd "$ROOT"
DEPLOY=1
[[ "${1:-}" == "--ohne-deploy" ]] && DEPLOY=0

PROJECT=p-yw5cv5
STACK=b8d0a6a8-83ef-4aba-b785-0b450c0ac551
REGISTRY=ghcr.io/herrlen/luibui
DOCKER=(docker --context "${DOCKER_CONTEXT:-desktop-linux}")
TESTDB=luibui-testdb
TESTDB_URL=postgresql+psycopg://postgres:ci@127.0.0.1:55432/postgres

schritt() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fehler() { printf '\033[31mFEHLER: %s\033[0m\n' "$*" >&2; exit 1; }

# --- 0. Stand ---------------------------------------------------------------------------------
schritt "Stand"
[[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ]] || fehler "nicht auf main"
git diff --quiet HEAD -- || fehler "nicht committete Änderungen an versionierten Dateien"
SHA="$(git rev-parse HEAD)"
TAG="sha-$SHA"
echo "Commit $(git log --oneline -1)"
"${DOCKER[@]}" info >/dev/null 2>&1 || fehler "Docker Desktop läuft nicht"

# --- 1. Prüfungen wie in der CI -------------------------------------------------------------
schritt "Prüfungen"
# A test database may already listen there (e.g. from Colima); otherwise start one in Desktop.
if ! nc -z 127.0.0.1 55432 2>/dev/null; then
  "${DOCKER[@]}" start "$TESTDB" >/dev/null 2>&1 \
    || "${DOCKER[@]}" run -d --name "$TESTDB" -e POSTGRES_PASSWORD=ci -p 127.0.0.1:55432:5432 postgres:17 >/dev/null
  for _ in $(seq 1 30); do
    "${DOCKER[@]}" exec "$TESTDB" pg_isready -U postgres >/dev/null 2>&1 && break
    sleep 1
  done
fi
uv run ruff check .
uv run ruff format --check .
uv run mypy packages apps/api apps/worker
[[ -n "${LUIBUI_GITLEAKS:-}" ]] || echo "Hinweis: LUIBUI_GITLEAKS nicht gesetzt, gitleaks-Tests werden übersprungen"
TEST_DATABASE_URL="$TESTDB_URL" uv run pytest -q
(cd apps/web && pnpm install --frozen-lockfile >/dev/null && pnpm lint && pnpm test && pnpm build >/dev/null)

# --- 2. Images aus dem Commit bauen ---------------------------------------------------------
schritt "Images bauen ($TAG)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
git archive HEAD | tar -x -C "$BUILD"
for s in api worker; do
  "${DOCKER[@]}" build --platform linux/amd64 -q -f "$BUILD/apps/$s/Dockerfile" \
    -t "$REGISTRY/$s:$TAG" -t "$REGISTRY/$s:main" "$BUILD"
done
"${DOCKER[@]}" build --platform linux/amd64 -q -f "$BUILD/apps/web/Dockerfile" \
  -t "$REGISTRY/web:$TAG" -t "$REGISTRY/web:main" "$BUILD/apps/web"

# --- 3. Push nach ghcr.io -------------------------------------------------------------------
schritt "Push nach ghcr.io"
gh auth token | "${DOCKER[@]}" login ghcr.io -u "$(gh api user -q .login)" --password-stdin >/dev/null
for s in api worker web; do
  "${DOCKER[@]}" push -q "$REGISTRY/$s:$TAG"
  "${DOCKER[@]}" push -q "$REGISTRY/$s:main"
done
"${DOCKER[@]}" logout ghcr.io >/dev/null

[[ $DEPLOY == 1 ]] || { echo "Fertig ohne Ausrollen."; exit 0; }

# --- 4. Ausrollen auf mittwald --------------------------------------------------------------
schritt "Ausrollen"
ENVFILE="$(mktemp)"
chmod 600 "$ENVFILE"
trap 'rm -rf "$BUILD"; rm -f "$ENVFILE"' EXIT
STATE="$(mw stack list -p "$PROJECT" -o json 2>/dev/null)"
env_of() { jq -r --arg s "$1" --arg k "$2" '.[0].services[] | select(.serviceName==$s) | .deployedState.envs[$k] // empty' <<<"$STATE"; }
PG="$(env_of postgres POSTGRES_PASSWORD)"
MK="$(env_of api MASTER_KEY)"
[[ -n "$PG" && -n "$MK" ]] || fehler "Secrets aus dem laufenden Stack nicht lesbar"
ANNAHME="${ANNAHME_OFFEN:-$(env_of api ANNAHME_OFFEN)}"
SMTP="${SMTP_PASSWORD:-$(env_of api SMTP_PASSWORD)}"
[[ -n "$SMTP" ]] || echo "Hinweis: SMTP_PASSWORD fehlt, das Kontaktformular antwortet mit 503"
{
  printf 'POSTGRES_PASSWORD=%s\n' "$PG"
  printf 'MASTER_KEY=%s\n' "$MK"
  printf 'IMAGE_TAG=%s\n' "$TAG"
  printf 'LUIBUI_ACCESS_LOG=0\n'
  printf 'ANNAHME_OFFEN=%s\n' "${ANNAHME:-false}"
  printf 'SMTP_PASSWORD=%s\n' "$SMTP"
} >"$ENVFILE"
unset STATE PG MK SMTP
echo "Annahme offen: ${ANNAHME:-false}"
mw stack deploy -s "$STACK" -c infra/mittwald-stack.yml --env-file "$ENVFILE" 2>&1 | grep -E "SUCCESS|rror" || true

# --- 5. Health ------------------------------------------------------------------------------
schritt "Health"
for _ in $(seq 1 60); do
  if curl -sf https://api.luibui.com/health | grep -q '"status":"ok"' \
    && curl -sf -o /dev/null https://luibui.com/; then
    curl -s https://api.luibui.com/health; echo
    mw stack ps -s "$STACK" 2>&1 | grep -E "^(api|worker|web)" | awk '{print $1, $2}'
    echo "Ausgerollt: $SHA"
    exit 0
  fi
  sleep 5
done
fehler "Health nach 5 Minuten nicht grün, bitte Container-Logs ansehen"
