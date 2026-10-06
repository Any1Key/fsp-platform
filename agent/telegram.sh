#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env

kind="${1:-}"
shift || true

enabled() {
  [[ "${TELEGRAM_ENABLED,,}" == "true" ]] &&
  [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] &&
  [[ -n "${TELEGRAM_CHAT_ID:-}" ]]
}

if ! enabled; then
  [[ "$kind" == "message" ]] && echo "[telegram disabled] $*"
  exit 0
fi

api="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

case "$kind" in
  message)
    text="$*"
    curl -fsS --max-time 20 \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${text}" \
      --data-urlencode "disable_web_page_preview=true" \
      "${api}/sendMessage" >/dev/null
    ;;
  photo)
    file="${1:?photo path required}"; shift
    caption="$*"
    [[ -f "$file" ]] || { echo "photo not found: $file" >&2; exit 2; }
    curl -fsS --max-time 60 \
      -F "chat_id=${TELEGRAM_CHAT_ID}" \
      -F "photo=@${file}" \
      -F "caption=${caption:0:1000}" \
      "${api}/sendPhoto" >/dev/null
    ;;
  document)
    file="${1:?document path required}"; shift
    caption="$*"
    [[ -f "$file" ]] || { echo "document not found: $file" >&2; exit 2; }
    curl -fsS --max-time 120 \
      -F "chat_id=${TELEGRAM_CHAT_ID}" \
      -F "document=@${file}" \
      -F "caption=${caption:0:1000}" \
      "${api}/sendDocument" >/dev/null
    ;;
  *)
    echo "usage: $0 message TEXT | photo FILE CAPTION | document FILE CAPTION" >&2
    exit 2
    ;;
esac
