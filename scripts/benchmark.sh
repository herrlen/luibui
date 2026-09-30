#!/usr/bin/env bash
# Benchmark (S3-2) in the worker image, where every scanner is installed: detection rate on the
# defused fixtures, false alarms on corpus/benign and the 60 open packages in corpus/vergleich.json.
#
#   scripts/benchmark.sh                   alles → docs/benchmark.md
#   scripts/benchmark.sh --ohne-vergleich  nur die eigenen Fixtures (ohne Netz, eine Minute)
#
# The engine and the rules come from the working tree (mounted read-only), the scanners from the
# image. The worker image has no git, so the open packages are fetched on this Mac first, through
# the same safe_git as in production, and handed to the container read-only. The OSV database lives in the Docker volume luibui-benchmark-osv and is refreshed at most
# once a day with the worker's own code. Needs Docker Desktop and an image from scripts/release.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"
DOCKER=(docker --context "${DOCKER_CONTEXT:-desktop-linux}")
IMAGE="${LUIBUI_WORKER_IMAGE:-ghcr.io/herrlen/luibui/worker:main}"
VOLUME=luibui-benchmark-osv
VERGLEICH=1
[[ "${1:-}" == "--ohne-vergleich" ]] && VERGLEICH=0

STAND="$(git -C "$ROOT" rev-parse --short HEAD)"
[[ -z "$(git -C "$ROOT" status --porcelain -- packages rules corpus)" ]] || STAND="$STAND+lokal"
OUT="$(mktemp -d)"
GEHOLT="$(mktemp -d)"
trap 'rm -rf "$OUT" "$GEHOLT"' EXIT
chmod 777 "$OUT"
ARGS=()
if [[ $VERGLEICH == 1 ]]; then
  echo "Echte Pakete holen …"
  (cd "$ROOT" && uv run --quiet python -m luibui_scan.benchmark corpus --holen "$GEHOLT")
  chmod -R a+rX "$GEHOLT"
  ARGS=(--vergleich /vergleich)
fi

"${DOCKER[@]}" volume create "$VOLUME" >/dev/null
echo "OSV-Datenbank prüfen …"
"${DOCKER[@]}" run --rm --platform linux/amd64 -v "$VOLUME":/rules/osv --entrypoint python "$IMAGE" -c \
  "from pathlib import Path; from luibui_worker import osvdb; print(osvdb.refresh(Path('/rules/osv'), 86400) or 'aktuell')"

echo "Benchmark läuft (Stand $STAND) …"
"${DOCKER[@]}" run --rm --platform linux/amd64 \
  -v "$ROOT":/repo:ro -v "$GEHOLT":/vergleich:ro -v "$VOLUME":/rules/osv:ro -v "$OUT":/out \
  -e PYTHONPATH=/repo/packages/engine -e LUIBUI_RULES_DIR=/repo/rules \
  --entrypoint python "$IMAGE" \
  -m luibui_scan.benchmark /repo/corpus ${ARGS[@]+"${ARGS[@]}"} --stand "$STAND" --ausgabe /out/benchmark.md \
  2>"$OUT/stderr.log" || { tail -30 "$OUT/stderr.log"; exit 1; }

cp "$OUT/benchmark.md" "$ROOT/docs/benchmark.md"
sed -n '/^## Ergebnis/,/^## Erkennung je Ebene/p' "$ROOT/docs/benchmark.md" | sed '$d'
echo "→ docs/benchmark.md"
