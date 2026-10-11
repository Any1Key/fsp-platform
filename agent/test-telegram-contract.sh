#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture="$(mktemp -d "$ROOT/.agent/telegram-test.XXXXXX")"
trap 'rm -rf "$fixture"' EXIT

mkdir -p "$fixture/agent" "$fixture/.agent/screenshots/latest" "$fixture/bin"
cp "$ROOT/agent/lib.sh" "$ROOT/agent/telegram.sh" "$fixture/agent/"
chmod 755 "$fixture/agent/telegram.sh"
printf '\x89PNG\r\n\x1a\nsynthetic screenshot bytes\n' > "$fixture/.agent/screenshots/latest/demo.png"
printf 'private document bytes\n' > "$fixture/private-resume.pdf"
printf 'not a png\n' > "$fixture/.agent/screenshots/latest/fake.png"

printf '%s\n' '#!/usr/bin/env bash' \
  'for arg in "$@"; do' \
  '  case "$arg" in' \
  '    https://api.telegram.org/*) printf "endpoint=%s\n" "${arg##*/}" >> "$TELEGRAM_FAKE_LOG" ;;' \
  '    *) printf "arg=%s\n" "$arg" >> "$TELEGRAM_FAKE_LOG" ;;' \
  '  esac' \
  'done' \
  > "$fixture/bin/curl"
chmod 755 "$fixture/bin/curl"

export PATH="$fixture/bin:$PATH"
export TELEGRAM_ENABLED=true
export TELEGRAM_BOT_TOKEN=synthetic-bot-token
export TELEGRAM_CHAT_ID=synthetic-chat-id
export TELEGRAM_CURL_BIN="$fixture/bin/curl"
export TELEGRAM_FAKE_LOG="$fixture/calls.log"

calls="$TELEGRAM_FAKE_LOG"

bash "$fixture/agent/telegram.sh" message \
  $'FSP runtime recovered\nRun: 20261011-000000\nEmail: candidate@example.com\nPhone: +7 900 123-45-67' \
  > "$calls"
grep -Fq 'arg=text=FSP watchdog recovered.' "$calls"
! grep -Eiq 'candidate@example.com|123-45-67|20261011-000000' "$calls"

if bash "$fixture/agent/telegram.sh" message 'raw resume text candidate@example.com' >> "$calls" 2>&1; then
  echo 'unknown or sensitive Telegram message was accepted' >&2
  exit 1
fi

if bash "$fixture/agent/telegram.sh" document "$fixture/private-resume.pdf" 'resume' >> "$calls" 2>&1; then
  echo 'Telegram document upload was accepted' >&2
  exit 1
fi
! grep -Fq 'endpoint=sendDocument' "$calls"

disabled_output="$(TELEGRAM_ENABLED=false bash "$fixture/agent/telegram.sh" message \
  $'FSP runtime recovered\nEmail: candidate@example.com')"
grep -Fq '[telegram disabled] FSP watchdog recovered.' <<< "$disabled_output"
! grep -Fq 'candidate@example.com' <<< "$disabled_output"

bash "$fixture/agent/telegram.sh" photo \
  "$fixture/.agent/screenshots/latest/demo.png" \
  'candidate@example.com' >> "$calls"
grep -Fq 'endpoint=sendPhoto' "$calls"
grep -Fq 'caption=FSP synthetic demo screenshot.' "$calls"
! grep -Fq 'candidate@example.com' "$calls"

if bash "$fixture/agent/telegram.sh" photo "$fixture/private-resume.pdf" 'caption' >> "$calls" 2>&1; then
  echo 'Telegram accepted a non-screenshot photo' >&2
  exit 1
fi

if bash "$fixture/agent/telegram.sh" photo \
  "$fixture/.agent/screenshots/latest/fake.png" 'caption' >> "$calls" 2>&1; then
  echo 'Telegram accepted a non-PNG screenshot artifact' >&2
  exit 1
fi

echo 'Telegram no-PII contract OK'
