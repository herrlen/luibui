#!/usr/bin/env bash
# luibui check in CI (S5-5): pack the package, upload it to the project with a project token,
# wait for the result, write SARIF and decide by the overall light. Inputs come only from the
# environment (never interpolated into the script). Needs bash, curl, jq and git or zip.
set -euo pipefail

api="${LUIBUI_API:-https://api.luibui.com}"
api="${api%/}"
token="${LUIBUI_TOKEN:?Projekt-Token fehlt (Eingabe token)}"
projekt="${LUIBUI_PROJEKT:?Projekt-ID fehlt (Eingabe projekt)}"
pfad="${LUIBUI_PFAD:-.}"
schwelle="${LUIBUI_SCHWELLE:-rot}"
sarif="${LUIBUI_SARIF:-luibui.sarif}"
zeitlimit="${LUIBUI_ZEITLIMIT:-900}"
takt="${LUIBUI_TAKT:-5}"
app="${LUIBUI_APP:-https://app.luibui.com}"
ausgabe="${GITHUB_OUTPUT:-/dev/null}"
zusammenfassung="${GITHUB_STEP_SUMMARY:-/dev/null}"

[[ "$projekt" =~ ^[0-9a-fA-F-]{36}$ ]] || { echo "::error::Ungültige Projekt-ID"; exit 2; }
case "$schwelle" in gesperrt|rot|gelb|nie) ;; *) echo "::error::schwelle: gesperrt, rot, gelb oder nie"; exit 2;; esac
[[ "$zeitlimit" =~ ^[0-9]+$ ]] || { echo "::error::zeitlimit muss eine Zahl sein"; exit 2; }
[[ "$api" == https://* || "$api" == http://127.0.0.1* || "$api" == http://localhost* ]] \
  || { echo "::error::api muss mit https:// beginnen"; exit 2; }
echo "::add-mask::$token"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
archiv="$tmp/paket.zip"

# Only files tracked by git (no node_modules, no build output); outside a repository all files.
if git -C "$pfad" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  prefix="$(git -C "$pfad" rev-parse --show-prefix)"
  wurzel="$(git -C "$pfad" rev-parse --show-toplevel)"
  git -C "$wurzel" archive --format=zip -o "$archiv" "HEAD:${prefix}"
else
  (cd "$pfad" && zip -qr "$archiv" . -x '.git/*')
fi

auth=(-H "Authorization: Bearer $token")
antwort="$tmp/antwort.json"
code="$(curl -sS -o "$antwort" -w '%{http_code}' "${auth[@]}" \
  -F art=zip -F "dateien=@$archiv;type=application/zip;filename=paket.zip" \
  "$api/api/v1/projects/$projekt/scans")"
if [[ "$code" != 202 ]]; then
  echo "::error::luibui hat die Prüfung nicht angenommen (HTTP $code): $(jq -r '.detail.text? // .detail? // empty' "$antwort" 2>/dev/null | head -c 300)"
  exit 1
fi
scan="$(jq -r .id "$antwort")"
[[ "$scan" =~ ^[0-9a-fA-F-]{36}$ ]] || { echo "::error::Unerwartete Antwort von luibui"; exit 1; }
echo "Prüfung $scan gestartet."

ende=$(( $(date +%s) + zeitlimit ))
while :; do
  code="$(curl -sS -o "$antwort" -w '%{http_code}' "${auth[@]}" "$api/api/v1/scans/$scan")"
  [[ "$code" == 200 ]] || { echo "::error::Status nicht lesbar (HTTP $code)"; exit 1; }
  status="$(jq -r .status "$antwort")"
  [[ "$status" == fertig || "$status" == fehlgeschlagen ]] && break
  if (( $(date +%s) >= ende )); then echo "::error::Zeitlimit von ${zeitlimit}s überschritten"; exit 1; fi
  sleep "$takt"
done

bericht="$app/pruefungen/$scan"
echo "bericht=$bericht" >> "$ausgabe"
if [[ "$status" == fehlgeschlagen ]]; then
  echo "::error::Die Prüfung ist fehlgeschlagen: $(jq -r '.fehler // ""' "$antwort" | head -c 300)"
  exit 1
fi

ampel="$(jq -r '.ampeln.gesamt // ""' "$antwort")"
note="$(jq -r '.note // ""' "$antwort")"
case "$ampel" in gruen|gelb|rot|gesperrt) ;; *) echo "::error::Unerwartete Ampel"; exit 1;; esac
[[ "$note" =~ ^[0-9]{1,3}$ ]] || note=""

code="$(curl -sS -o "$sarif" -w '%{http_code}' "${auth[@]}" "$api/api/v1/scans/$scan/bericht.sarif")"
[[ "$code" == 200 ]] || { echo "::error::SARIF nicht lesbar (HTTP $code)"; exit 1; }
{
  echo "ampel=$ampel"
  echo "note=$note"
  echo "sarif=$sarif"
} >> "$ausgabe"

befunde="$(jq '[.runs[0].results[] | select(.suppressions == null)] | length' "$sarif")"
{
  echo "### luibui-Prüfung"
  echo
  echo "| Gesamtampel | Note | Offene Befunde |"
  echo "| --- | --- | --- |"
  echo "| $ampel | ${note:-–} | $befunde |"
  echo
  echo "[Zum Bericht]($bericht)"
} >> "$zusammenfassung"
echo "Gesamtampel: $ampel, Note: ${note:-–}, offene Befunde: $befunde"
echo "Bericht: $bericht"

rang() { case "$1" in gruen) echo 0;; gelb) echo 1;; rot) echo 2;; gesperrt) echo 3;; *) echo 9;; esac; }
if [[ "$schwelle" != nie ]] && (( $(rang "$ampel") >= $(rang "$schwelle") )); then
  echo "::error::Gesamtampel $ampel erreicht die Schwelle $schwelle"
  exit 1
fi
