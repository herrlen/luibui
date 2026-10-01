#!/usr/bin/env bash
# Local release with Docker Desktop instead of GitHub Actions: check, build, push, deploy.
#
#   scripts/release.sh                 alles: Prüfungen, Images, Push, Ausrollen
#   scripts/release.sh --ohne-deploy   nur prüfen, bauen und pushen
#
# Builds exactly the committed state (git archive HEAD), never the working tree. Before the
# rollout the new images are pulled onto the server by short-lived containers: mittwald stops the
# old container first and pulls afterwards, so an image that is already there shortens the gap
# from about 20 s to a few seconds (measured 30.09.2026). The rollout counts as done only when
# api and web report the new version; the gap is measured and printed.
# Secrets are read
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
uv run mypy packages apps/api apps/worker apps/ops
[[ -n "${LUIBUI_GITLEAKS:-}" ]] || echo "Hinweis: LUIBUI_GITLEAKS nicht gesetzt, gitleaks-Tests werden übersprungen"
TEST_DATABASE_URL="$TESTDB_URL" uv run pytest -q
(cd apps/web && pnpm install --frozen-lockfile >/dev/null && pnpm lint && pnpm test && pnpm build >/dev/null)

# --- 2. Images aus dem Commit bauen ---------------------------------------------------------
schritt "Images bauen ($TAG)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
git archive HEAD | tar -x -C "$BUILD"
for s in api worker ops; do
  "${DOCKER[@]}" build --platform linux/amd64 -q -f "$BUILD/apps/$s/Dockerfile" \
    --build-arg LUIBUI_VERSION="$TAG" -t "$REGISTRY/$s:$TAG" -t "$REGISTRY/$s:main" "$BUILD"
done
"${DOCKER[@]}" build --platform linux/amd64 -q -f "$BUILD/apps/web/Dockerfile" \
  --build-arg LUIBUI_VERSION="$TAG" -t "$REGISTRY/web:$TAG" -t "$REGISTRY/web:main" "$BUILD/apps/web"

# --- 3. Push nach ghcr.io -------------------------------------------------------------------
schritt "Push nach ghcr.io"
gh auth token | "${DOCKER[@]}" login ghcr.io -u "$(gh api user -q .login)" --password-stdin >/dev/null
for s in api worker web ops; do
  "${DOCKER[@]}" push -q "$REGISTRY/$s:$TAG"
  "${DOCKER[@]}" push -q "$REGISTRY/$s:main"
done
"${DOCKER[@]}" logout ghcr.io >/dev/null

[[ $DEPLOY == 1 ]] || { echo "Fertig ohne Ausrollen."; exit 0; }

# --- 4. Ausrollen auf mittwald --------------------------------------------------------------
schritt "Konfiguration"
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
# PayPal: ~/.config/luibui/paypal.env (never in the repo) wins over the deployed values.
PAYPAL_DATEI="${HOME}/.config/luibui/paypal.env"
if [[ -f "$PAYPAL_DATEI" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$PAYPAL_DATEI"; set +a
fi
PP_ID="${PAYPAL_CLIENT_ID:-$(env_of api PAYPAL_CLIENT_ID)}"
PP_SECRET="${PAYPAL_SECRET:-$(env_of api PAYPAL_SECRET)}"
PP_MODUS="${PAYPAL_MODUS:-$(env_of api PAYPAL_MODUS)}"
PP_WEBHOOK="${PAYPAL_WEBHOOK_ID:-$(env_of api PAYPAL_WEBHOOK_ID)}"
# Backup and alarm (S3-10): ~/.config/luibui/ops.env (BACKUP_AGE_RECIPIENT, ALARM_AN) wins over the
# deployed values. Only the age PUBLIC key goes to the server; the private key stays with Len.
OPS_DATEI="${HOME}/.config/luibui/ops.env"
if [[ -f "$OPS_DATEI" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$OPS_DATEI"; set +a
fi
BACKUP_KEY="${BACKUP_AGE_RECIPIENT:-$(env_of ops BACKUP_AGE_RECIPIENT)}"
ALARM="${ALARM_AN:-$(env_of ops ALARM_AN)}"
[[ -n "$BACKUP_KEY" ]] && echo "Backup: eingerichtet" || echo "Hinweis: BACKUP_AGE_RECIPIENT fehlt, es laufen keine Backups (docs/restore.md)"
[[ -n "$ALARM" ]] || echo "Hinweis: ALARM_AN fehlt, Alarme stehen nur im Log des ops-Containers"
[[ -n "$PP_ID" && -n "$PP_SECRET" ]] && echo "PayPal: eingerichtet (${PP_MODUS:-live})" || echo "Hinweis: PayPal nicht eingerichtet, Guthaben-Grenzen sind aus"
[[ -n "$SMTP" ]] || echo "Hinweis: SMTP_PASSWORD fehlt, das Kontaktformular antwortet mit 503"
{
  printf 'POSTGRES_PASSWORD=%s\n' "$PG"
  printf 'MASTER_KEY=%s\n' "$MK"
  printf 'IMAGE_TAG=%s\n' "$TAG"
  printf 'LUIBUI_ACCESS_LOG=0\n'
  printf 'ANNAHME_OFFEN=%s\n' "${ANNAHME:-false}"
  printf 'SMTP_PASSWORD=%s\n' "$SMTP"
  printf 'PAYPAL_CLIENT_ID=%s\n' "$PP_ID"
  printf 'PAYPAL_SECRET=%s\n' "$PP_SECRET"
  printf 'PAYPAL_MODUS=%s\n' "${PP_MODUS:-live}"
  printf 'PAYPAL_WEBHOOK_ID=%s\n' "$PP_WEBHOOK"
  printf 'BACKUP_AGE_RECIPIENT=%s\n' "$BACKUP_KEY"
  printf 'ALARM_AN=%s\n' "$ALARM"
} >"$ENVFILE"
unset STATE PG MK SMTP PP_ID PP_SECRET PP_WEBHOOK BACKUP_KEY ALARM
echo "Annahme offen: ${ANNAHME:-false}"

# Pull the new images onto the server while the old containers still serve. Each helper runs
# `true` and stops; it is deleted right away (also leftovers of an aborted run).
schritt "Images vorladen"
vorladen_weg() {
  mw container list -p "$PROJECT" -o json 2>/dev/null \
    | jq -r '.[] | select((.serviceName // .name // "") | startswith("vorladen-")) | .id' \
    | while read -r id; do mw container delete "$id" -p "$PROJECT" --force >/dev/null 2>&1 || true; done
}
vorladen_weg
for s in api worker web ops; do
  start=$SECONDS
  if mw container run -q -p "$PROJECT" --name "vorladen-$s" --entrypoint true \
    --description "luibui – Image vorladen, wird gleich gelöscht" "$REGISTRY/$s:$TAG" >/dev/null 2>&1; then
    echo "$s: $((SECONDS - start)) s"
  else
    echo "Hinweis: $s nicht vorgeladen, das Ausrollen dauert dann länger"
  fi
done
vorladen_weg

# Measure the gap: one request every half second to web and api until both run the new version.
PROBE="$(mktemp)"
PROBE_PID=""
trap 'touch "$PROBE.stop"; [[ -n "$PROBE_PID" ]] && kill "$PROBE_PID" 2>/dev/null || true; rm -rf "$BUILD"; rm -f "$ENVFILE" "$PROBE" "$PROBE.stop"' EXIT
(
  while [[ ! -f "$PROBE.stop" ]]; do
    printf '%s %s %s\n' "$(perl -MTime::HiRes=time -e 'printf "%.2f", time')" \
      "$(curl -s -o /dev/null -m 2 -w '%{http_code}' https://luibui.com/healthz)" \
      "$(curl -s -o /dev/null -m 2 -w '%{http_code}' https://api.luibui.com/health)" >>"$PROBE"
    sleep 0.5
  done
) &
PROBE_PID=$!

schritt "Ausrollen"
mw stack deploy -s "$STACK" -c infra/mittwald-stack.yml --env-file "$ENVFILE" 2>&1 | grep -E "SUCCESS|rror" || true

# --- 5. Health: done only when api and web run the new version ---------------------------------
schritt "Health"
version_von() { curl -sf -m 5 "$1" | jq -r '.version // empty' 2>/dev/null || true; }
neu=0
for _ in $(seq 1 100); do
  if curl -sf -m 5 https://api.luibui.com/health | grep -q '"status":"ok"' \
    && [[ "$(version_von https://api.luibui.com/health)" == "$TAG" ]] \
    && [[ "$(version_von https://luibui.com/healthz)" == "$TAG" ]] \
    && [[ "$(version_von https://app.luibui.com/healthz)" == "$TAG" ]]; then
    neu=1
    break
  fi
  sleep 3
done
sleep 5 # a few more samples after the switch
touch "$PROBE.stop"
wait "$PROBE_PID" 2>/dev/null || true
rm -f "$PROBE.stop"
# Seconds from each failed request to the next sample, summed per column (2 = web, 3 = api).
luecke() {
  awk -v spalte="$1" 'NR > 1 && fehl { summe += $1 - vorher } { fehl = ($spalte != 200); vorher = $1 }
    END { printf "%.1f", summe }' "$PROBE"
}
echo "Unterbrechung: Web $(luecke 2) s, API $(luecke 3) s"
[[ $neu == 1 ]] || fehler "Nach 5 Minuten läuft nicht überall $TAG, bitte Container-Logs ansehen"
curl -s https://api.luibui.com/health; echo
mw stack ps -s "$STACK" 2>&1 | grep -E "^(api|worker|web|ops)" | awk '{print $1, $2}'
echo "Ausgerollt: $SHA"
