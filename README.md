# FSP Talent Platform — submission repository

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
- runnable `Next.js + FastAPI + PostgreSQL + Keycloak` modular monolith;
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
5. Запусти:
   ```bash
   docker compose up -d --build
   ./agent/wait-http.sh http://127.0.0.1:8000/health/ready 240
   ./agent/wait-http.sh http://127.0.0.1:3000/api/health 240
   ```

## Режимы

- Интерактивный Codex: см. `CODEX_START.md`.
- Полный автономный цикл: `./agent/autopilot.sh`.
- Только верификация: `./agent/verify.sh`.
- Скриншоты: `./agent/capture-screenshots.sh`.
- Telegram test: `./agent/telegram.sh message "FSP agent online"`.

## Submission status

Implemented slices cover identity, `.ru` registration, candidate evidence and assessment, FSP,
Talent Radar/ProofMatch, salary invitations, accepted matches, internal chat, employer tasks,
privacy controls, optional CPU-local AI, validation, and responsive public evidence. Exact remaining
P0 gaps and supervisor-owned verification gates are recorded in `.agent/STATUS.md` and
`docs/REQUIREMENTS_MATRIX.md`; this repository must not be labelled `READY` until those gates pass.

For the jury sequence and manual checkpoints, use `docs/DEMO_SCENARIO.md`. For a repeatable empty
database baseline, use `DEMO_RESET_CONFIRM=YES ./scripts/demo-reset.sh`; it never creates real
identities or sends real email.
