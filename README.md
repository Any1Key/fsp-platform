# FSP Talent Platform

Веб-платформа для подбора ИТ-специалистов по подтверждённым навыкам. Работодатель формирует потребность, получает объяснимую подборку кандидатов и отправляет приглашение с зарплатным диапазоном. После принятия приглашения создаётся match, открываются контакты и внутренний чат.

Проект состоит из Next.js frontend, FastAPI backend, PostgreSQL, Keycloak/OIDC и Docker Compose. Основной сценарий работает без GPU и без внешнего AI-сервиса.

## Возможности

- регистрация и подтверждение email через Keycloak;
- ограничение регистрации адресами в домене `.ru`;
- роли кандидата и работодателя с отдельными кабинетами;
- профиль, PDF-резюме и стандартизированный PDF-профиль;
- отрасль, специализация, заявленный грейд и системное тестирование;
- уникальные формы assessment с сопоставимой калибровкой и защитой от утечки;
- Verified Skill Passport и заменяемый синтетический адаптер FSP;
- Talent Radar и объяснимый ProofMatch;
- приглашения с обязательным диапазоном зарплаты в рублях;
- публикация вакансий и отклики;
- match, разблокировка контактов и внутренний чат;
- этапы найма, задания работодателя и оценка результата;
- privacy/consent, minor-consent и ограничения доступа;
- OpenAPI, синтетическая валидация, responsive UI и Playwright-проверки;
- опциональный локальный CPU-AI с ручным deterministic fallback.

## Требования

- Docker Engine 24+ и Docker Compose v2;
- Git;
- для production: домен, TLS reverse proxy и внешняя Docker-сеть, подключённая к reverse proxy.

## Локальный запуск

```bash
git clone <repository-url>
cd fsp-platform
cp .env.example .env
```

В `.env` замените значения `CHANGE_ME_*` и оставьте локальные URL:

```dotenv
APP_ENV=development
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_PUBLIC_URL=http://localhost:8081
KEYCLOAK_ISSUER=http://localhost:8081/realms/fsp
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Запустите сервисы:

```bash
docker compose config -q
docker compose up -d --build
docker compose ps
```

Адреса локального запуска:

| Компонент | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend health | http://localhost:8000/health |
| Backend readiness | http://localhost:8000/health/ready |
| Swagger/OpenAPI | http://localhost:8000/docs |
| Keycloak | http://localhost:8081 |
| Mailpit | http://localhost:8025 |

Остановка без удаления данных:

```bash
docker compose down
```

Не используйте `docker compose down -v`, если нужно сохранить PostgreSQL, Keycloak и private-storage volumes.

## Production-развёртывание

Production не содержит домена в исходниках. Все публичные адреса задаются в `.env`:

```dotenv
APP_ENV=production
APP_BASE_URL=https://your-domain.example
NEXT_PUBLIC_API_URL=https://your-domain.example
NEXT_PUBLIC_KEYCLOAK_URL=https://your-domain.example/auth
KEYCLOAK_PUBLIC_URL=https://your-domain.example/auth
KEYCLOAK_ISSUER=https://your-domain.example/auth/realms/fsp
KEYCLOAK_JWKS_URL=http://keycloak:8080/auth/realms/fsp/protocol/openid-connect/certs
CORS_ALLOWED_ORIGINS=https://your-domain.example
PROXY_NETWORK=your_reverse_proxy_network
```

`PROXY_NETWORK` — имя внешней Docker-сети, к которой подключён reverse proxy. Это deployment-настройка, а не фиксированное имя проекта.

В reverse proxy направьте:

- `/` на `frontend:3000`;
- `/api/*` на `backend:8000`;
- `/auth/*` на `keycloak:8080`.

Для Keycloak задайте hostname с путём `/auth` и передавайте `X-Forwarded-Proto: https` и `X-Forwarded-Host`. TLS завершается на reverse proxy.

Запуск:

```bash
docker compose -f docker-compose.yml -f compose.prod.yml config -q
docker compose -f docker-compose.yml -f compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f compose.prod.yml ps
```

После изменения любого `NEXT_PUBLIC_*` значения frontend нужно пересобрать: restart контейнера не меняет значения, уже встроенные в Next.js bundle.

### Keycloak client

Для клиента `fsp-web` в Keycloak должны совпадать с выбранным доменом:

- Valid redirect URIs: `https://your-domain.example/*`;
- Web origins: `https://your-domain.example`;
- client type: public;
- standard authorization code flow: enabled;
- direct access grants: disabled.

При первом запуске realm импортируется из `infrastructure/keycloak/realm-fsp.json`. Если realm уже существует в PostgreSQL, изменение JSON автоматически его не изменяет. В этом случае обновите существующий client через Keycloak Admin Console или `kcadm`, не удаляя realm и database.

Проверьте, что `KEYCLOAK_ISSUER` в точности совпадает с claim `iss` в access token. Backend получает JWKS по внутреннему Docker URL, а браузер использует публичный `KEYCLOAK_PUBLIC_URL`.

## Email verification

В локальном/demo-режиме Mailpit принимает письма на SMTP-порту 1025 и показывает их в интерфейсе на порту 8025. Зарегистрируйте `.ru` адрес, откройте письмо подтверждения в Mailpit и перейдите по ссылке.

Focused E2E-проверка production OIDC:

```bash
docker compose -f docker-compose.yml -f compose.prod.yml --profile test run --build --rm \
  -e KEYCLOAK_E2E_BASE_URL=http://keycloak:8080/auth \
  -e KEYCLOAK_PUBLIC_E2E_BASE_URL=https://your-domain.example/auth \
  -e FRONTEND_E2E_REDIRECT_URI=https://your-domain.example/ \
  -e E2E_FRONTEND_ORIGIN=https://your-domain.example \
  qa npx playwright test tests/auth-registration.spec.ts --project=desktop-1920 --retries=0
```

## Миграции и demo data

Backend применяет Alembic migrations перед запуском API. Проверка вручную:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
```

Детерминированный empty-database reset является destructive-операцией и удаляет volumes только этого Compose-проекта. Выполняйте его только для отдельного demo-окружения:

```bash
DEMO_RESET_CONFIRM=YES ./scripts/demo-reset.sh
```

Для обычного обновления проекта volumes не удаляются.

## Проверки

```bash
# Backend targeted tests
docker compose exec -T backend pytest -q tests/test_invitations.py tests/test_chat.py tests/test_employer_tasks.py tests/test_employer_evaluations.py

# Assessment tests
docker compose exec -T backend pytest -q tests/test_assessments.py

# Public QA smoke suite
docker compose -f docker-compose.yml -f compose.prod.yml --profile test run --build --rm qa \
  npx playwright test tests/smoke.spec.ts tests/security-headers.spec.ts tests/fsp-brand.spec.ts \
  --project=desktop-1920 --retries=0

# Full configured QA suite
docker compose --profile test run --build --rm qa npm test
```

Full backend pytest suite и длительный load test не требуются для каждой локальной правки. Для release-проверки используйте [матрицу требований](docs/REQUIREMENTS_MATRIX.md) и [сценарий демонстрации](docs/DEMO_SCENARIO.md).

## Документация

- [Техническое задание](docs/source/TZ_EXTRACTED.txt)
- [Матрица требований](docs/REQUIREMENTS_MATRIX.md)
- [Аудит документации](docs/DOCUMENTATION_AUDIT.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [API/OpenAPI](docs/API_GUIDELINES.md)
- [Assessment engine](docs/ASSESSMENT_ENGINE.md)
- [Matching engine](docs/MATCHING_ENGINE.md)
- [Chat and matching](docs/CHAT_AND_MATCHING.md)
- [FSP integration](docs/FSP_INTEGRATION.md)
- [Validation results](docs/VALIDATION_RESULTS.md)
- [Performance testing](docs/PERFORMANCE_TESTING.md)
- [Security](docs/SECURITY.md)
- [Presentation outline](docs/PRESENTATION_OUTLINE.md)

## Структура проекта

```text
backend/                 FastAPI API, domain logic, migrations and tests
frontend/                Next.js application
qa/                      Playwright smoke and E2E checks
infrastructure/keycloak Keycloak realm template
docs/                    TZ, architecture, API and validation documents
scripts/                 deployment and demo utilities
compose.prod.yml         production network/URL override
docker-compose.yml       local and test Compose profile
```

## Статус

Основные P0/P1 механики реализованы и покрыты targeted/backend/QA проверками. Перед формальным статусом `READY` остаются единый authenticated DEMO-001 E2E-сценарий, фактический target load report и экспорт финальной презентации в PDF или PPTX. Подробный статус находится в [DOCUMENTATION_AUDIT.md](docs/DOCUMENTATION_AUDIT.md).
