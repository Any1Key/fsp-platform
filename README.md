# FSP Talent Platform — autonomous Codex bootstrap

Стартовый репозиторий для автономной разработки цифровой платформы подбора ИТ-специалистов по ТЗ ФСП 2026.

## Уже подготовлено

- исходное ТЗ в `docs/source/`;
- формализованная матрица требований;
- продуктовая и техническая архитектура;
- дизайн-система по официальному брендбуку ФСП;
- концепция уникального calibrated assessment + anti-leak/anti-AI-by-design;
- ProofMatch / Evidence-Graph Reverse Matching + Talent Radar;
- employer hiring pipeline, post-match chat and CPU-local AI task-copilot design;
- conference Q&A clarifications from 2026-10-06 integrated into requirements;
- runnable skeleton `Next.js + FastAPI + PostgreSQL + Keycloak`;
- Docker Compose для локального/демо запуска без обязательного GPU;
- Playwright для E2E и скриншотов desktop/tablet/mobile;
- supervisor вокруг `codex exec`;
- recovery-loop: код → build → services → tests → logs → repair → retry;
- Telegram-репортинг статусов и скриншотов;
- Git checkpoint/push после успешной верификации;
- backlog/milestones и критерии `READY`.

## Главный принцип

Codex не может сам объявить работу проверенной. Статус `VERIFIED` выставляется только после реального
`docker compose build/up`, health checks, тестов и E2E внешним supervisor.

## Быстрый старт

1. Прочитай `docs/SETUP_SYNOLOGY_CODEX_RU.md`.
2. `cp .env.example .env`
3. `cp .env.agent.example .env.agent`
4. Заполни секреты локально.
5. Выполни:
   ```bash
   ./agent/doctor.sh
   ./agent/autopilot.sh
   ```

## Режимы

- Интерактивный Codex: см. `CODEX_START.md`.
- Полный автономный цикл: `./agent/autopilot.sh`.
- Только верификация: `./agent/verify.sh`.
- Скриншоты: `./agent/capture-screenshots.sh`.
- Telegram test: `./agent/telegram.sh message "FSP agent online"`.

## Что является готовым сейчас

Приложение содержит только рабочий bootstrap/smoke-каркас. Полная бизнес-функциональность намеренно
оставлена Codex: этот репозиторий — управляемая спецификация, среда разработки, контроль качества и
агентный контур.
