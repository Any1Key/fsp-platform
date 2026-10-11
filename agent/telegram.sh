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

safe_message() {
  local raw="$*"
  case "$raw" in
    *"FSP Codex supervisor: Telegram OK"*)
      printf '%s' 'FSP telemetry connection check.'
      ;;
    *"FSP runtime watchdog started"*)
      printf '%s' 'FSP watchdog started.'
      ;;
    *"FSP runtime health failure"*)
      printf '%s' 'FSP watchdog health failure.'
      ;;
    *"FSP runtime recovered"*)
      printf '%s' 'FSP watchdog recovered.'
      ;;
    *"FSP runtime watchdog BLOCKED"*)
      printf '%s' 'FSP watchdog blocked.'
      ;;
    *"FSP Codex supervisor started"*)
      printf '%s' 'FSP supervisor started.'
      ;;
    *"FSP Platform state is READY"*)
      printf '%s' 'FSP platform is ready.'
      ;;
    *"FSP agent cycle"*)
      printf '%s' 'FSP agent cycle started.'
      ;;
    *"FSP execution failed"*)
      printf '%s' 'FSP agent execution failed.'
      ;;
    *"FSP recovery"*)
      printf '%s' 'FSP recovery attempt started.'
      ;;
    *"FSP agent BLOCKED"*)
      printf '%s' 'FSP agent blocked.'
      ;;
    *"FSP cycle verified"*)
      printf '%s' 'FSP cycle verified.'
      ;;
    *"MAX_AGENT_CYCLES"*)
      printf '%s' 'FSP supervisor reached its cycle limit.'
      ;;
    *)
      return 1
      ;;
  esac
}

safe_screenshot_path() {
  local file="$1"
  local screenshot_root resolved root_real signature
  [[ -f "$file" && ! -L "$file" ]] || {
    echo "Telegram photo must be a regular generated screenshot file." >&2
    return 2
  }
  screenshot_root="$ROOT/.agent/screenshots/latest"
  [[ -d "$screenshot_root" ]] || {
    echo "Telegram screenshot directory is unavailable." >&2
    return 2
  }
  root_real="$(cd -- "$screenshot_root" && pwd -P)"
  resolved="$(cd -- "$(dirname -- "$file")" && pwd -P)/$(basename -- "$file")"
  case "$resolved" in
    "$root_real"/*.png) ;;
    *)
      echo "Telegram photos are restricted to generated screenshots." >&2
      return 2
      ;;
  esac
  signature="$(head -c 8 "$resolved" | od -An -t x1 | tr -d ' \n')"
  [[ "$signature" == '89504e470d0a1a0a' ]] || {
    echo "Telegram photo must have a PNG signature." >&2
    return 2
  }
  printf '%s' "$resolved"
}

safe_text=''
if [[ "$kind" == "message" ]]; then
  safe_text="$(safe_message "$@")" || {
    echo "Telegram message rejected: use a known supervisor event." >&2
    exit 2
  }
elif [[ "$kind" == "document" ]]; then
  echo "Telegram document reporting is disabled; keep documents in local evidence storage." >&2
  exit 2
fi

if ! enabled; then
  [[ "$kind" == "message" ]] && echo "[telegram disabled] $safe_text"
  exit 0
fi

api="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"
telegram_curl="${TELEGRAM_CURL_BIN:-curl}"

case "$kind" in
  message)
    "$telegram_curl" -fsS --max-time 20 \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${safe_text}" \
      --data-urlencode "disable_web_page_preview=true" \
      "${api}/sendMessage" >/dev/null
    ;;
  photo)
    file="${1:?photo path required}"; shift
    file="$(safe_screenshot_path "$file")"
    "$telegram_curl" -fsS --max-time 60 \
      -F "chat_id=${TELEGRAM_CHAT_ID}" \
      -F "photo=@${file}" \
      -F 'caption=FSP synthetic demo screenshot.' \
      "${api}/sendPhoto" >/dev/null
    ;;
  document)
    echo "Telegram document reporting is disabled; keep documents in local evidence storage." >&2
    exit 2
    ;;
  *)
    echo "usage: $0 message TEXT | photo FILE CAPTION | document FILE CAPTION" >&2
    exit 2
    ;;
esac
