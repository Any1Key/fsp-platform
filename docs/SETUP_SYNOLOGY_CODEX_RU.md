# Подробная подготовка Synology + GitHub + Codex

Инструкция рассчитана на DSM 7.x с Container Manager и SSH. Текущий целевой профиль проекта: около 8 CPU и 32–64 GB RAM; GPU не требуется.

## 0. Что делает контур

Codex изменяет рабочий репозиторий. Внешний supervisor:
1. запускает `codex exec`;
2. собирает проект через Docker Compose;
3. поднимает сервисы;
4. ждёт health checks;
5. запускает unit/integration/E2E;
6. при ошибке сохраняет логи и отправляет Codex на repair;
7. повторяет до успеха или лимита;
8. делает responsive screenshots;
9. отправляет статусы/скриншоты в Telegram;
10. при включённом `AUTO_PUSH` делает checkpoint и push в GitHub.

## 1. Подготовь Synology

В Package Center установи **Container Manager**.

Включи SSH:
`Control Panel → Terminal & SNMP → Enable SSH`.

Желательно создать отдельного пользователя, например `fsp-agent`.
Не запускай Codex под `root` и по возможности не используй DSM admin-учётку.

Рабочий каталог:

```bash
mkdir -p /volume1/docker/fsp-platform
cd /volume1/docker/fsp-platform
```

Проверь:

```bash
docker --version
docker compose version
git --version
uname -m
```

Если `docker compose` недоступен, сначала реши это на уровне Container Manager/DSM.

## 2. Установи Codex CLI

Актуальный официальный способ для Linux:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Альтернатива при наличии Node/npm:

```bash
npm install -g @openai/codex@latest
```

Проверь:

```bash
codex --version
```

Официальные standalone binaries также публикуются для Linux `x86_64` и `arm64`.
Если installer не дружит с Synology userspace, используй бинарник под архитектуру `uname -m`.

## 3. Авторизуй Codex

Под тем же Unix-пользователем, под которым будет работать supervisor:

```bash
codex
```

Выбери **Sign in with ChatGPT** и заверши вход.

Проверь:

```bash
codex login status
```

Автоматический `codex exec` должен работать под тем же пользователем, иначе он может не увидеть сохранённую сессию.

Не помещай OpenAI/Codex credentials в Git.

## 4. Подготовь GitHub

Создай пустой repository, например `fsp-platform`.

Если начинаешь из распакованного bootstrap:

```bash
cd /volume1/docker/fsp-platform
git init
git branch -M main
git remote add origin git@github.com:YOUR_USER/fsp-platform.git
```

Рекомендуется отдельный SSH key:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_fsp -C "fsp-agent"
cat ~/.ssh/id_ed25519_fsp.pub
```

Добавь public key в GitHub и проверь:

```bash
ssh -T git@github.com
```

Если repository уже существует, используй `git clone`.

## 5. Распакуй bootstrap

Скопируй содержимое ZIP в:

```text
/volume1/docker/fsp-platform
```

Затем:

```bash
cd /volume1/docker/fsp-platform
chmod +x agent/*.sh scripts/*.sh
```

## 6. Настрой приложение

```bash
cp .env.example .env
vi .env
```

Замени все `CHANGE_ME_*`.

Сгенерировать пароли:

```bash
openssl rand -base64 32
```

`.env` уже исключён из Git.

Если проект будет открываться не через `localhost`, Codex в одном из ранних milestones должен привести
Keycloak redirect/web origins и публичные URL к реальному имени/IP demo-хоста.

## 7. Создай Telegram-бота

В Telegram открой `@BotFather`:
1. `/newbot`
2. укажи имя;
3. username, заканчивающийся на `bot`;
4. сохрани token.

Напиши боту любое сообщение.

Узнай `chat_id`:

```bash
curl -s "https://api.telegram.org/bot<ТОКЕН>/getUpdates"
```

Найди:

```json
"chat":{"id":123456789}
```

Создай agent env:

```bash
cp .env.agent.example .env.agent
vi .env.agent
```

Заполни:

```text
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Проверка:

```bash
./agent/telegram.sh message "FSP Codex supervisor: Telegram OK"
```

Токен не вставляй в prompts и не коммить.

## 8. Проверь стартовый Docker Compose

```bash
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Открой:
- `http://NAS_IP:3000`
- `http://NAS_IP:8000/docs`
- `http://NAS_IP:8081`
- `http://NAS_IP:8025`

Bootstrap должен показывать стартовую FSP-страницу и health endpoint.

Остановить:

```bash
docker compose down
```

## 9. Проверь supervisor

```bash
./agent/doctor.sh
```

Исправь все `FAIL`.

## 10. Первый контролируемый Codex run

Сначала рекомендую один ручной цикл:

```bash
codex
```

Вставь prompt из `CODEX_START.md`.

После завершения:

```bash
./agent/verify.sh
```

Если это успешно, окружение готово к автономной работе.

## 11. Запусти автономную разработку

```bash
./agent/autopilot.sh
```

По умолчанию:
- Codex берёт один coherent work unit;
- supervisor собирает/запускает реальный код;
- тестирует;
- при падении делает до 5 repair attempts;
- сохраняет логи;
- снимает screenshots;
- отправляет Telegram status.

Логи:

```text
.agent/runs/<run-id>/
```

Скриншоты:

```text
.agent/screenshots/latest/
```

Остановить: `Ctrl+C`.

## 12. Git push

В начале оставь:

```text
AUTO_PUSH=false
```

После нескольких успешных циклов проверь историю и затем:

```text
AUTO_PUSH=true
```

Supervisor работает в ветке:

```text
agent/autonomous
```

Не включай автоматический push непосредственно в `main`.

## 13. Работа после закрытия SSH

На Synology можно использовать Task Scheduler:

`Control Panel → Task Scheduler → Create → Triggered Task → User-defined script`

User: отдельный `fsp-agent`.

Script:

```bash
cd /volume1/docker/fsp-platform
nohup ./agent/autopilot.sh >> .agent/autopilot.out 2>&1 &
```

Supervisor использует lock-directory; второй экземпляр не должен запускаться одновременно.

## 14. Мониторинг

```bash
tail -f .agent/autopilot.out
docker compose ps
docker compose logs -f --tail=100
```

Telegram даёт основные события и UI screenshots.

## 15. Если repair исчерпал лимит

```bash
ls -1t .agent/runs | head
```

Посмотри последний:
- `verification.log`
- `compose.log`
- `codex.stderr`
- `repair-*-last.txt`

Blocker также появится в `.agent/PROBLEMS.md`.

## 16. Фирменные дополнительные assets

Архив уже содержит переданные логотипы и фото.

Чтобы получить опубликованные на официальном сайте графические элементы:

```bash
./scripts/fetch-brand-assets.sh
```

Они попадут в:

```text
frontend/public/brand/official/
```

Codex должен использовать их по `docs/BRAND_GUIDE.md`, а не как случайный декор.

## 17. Безопасность NAS

Важно:
- Codex не root;
- не монтировать `/volume1` целиком;
- не монтировать `/var/run/docker.sock` в frontend/backend;
- не хранить DSM admin password в `.env`;
- не публиковать 3000/8000/8081 напрямую в Интернет;
- для внешнего demo использовать reverse proxy + HTTPS;
- до длинного автономного запуска иметь бэкап repository/DB.

## 18. Новые требования из conference Q&A

В bootstrap уже включены уточнения 2026-10-06: уникальные тесты, anti-AI-by-design, `.ru` registration, working Keycloak demo, minor-consent flow, FSP achievements в ranking, ProofMatch, employer hiring pipeline, post-match chat и обязательный load test.

Core должен работать при:

```text
LOCAL_AI_ENABLED=false
```

Локальный AI — только optional CPU worker. Не ставь GPU/CUDA-зависимости. Если включаешь локальную модель, сначала заверши P0 core и проверь свободную RAM.

Telegram screenshots и сообщения агента должны использовать только synthetic/demo accounts; не отправляй туда реальные резюме, чаты, контакты или документы несовершеннолетних.

## 19. Что считать финалом

Не фразу Codex "готово".

Финал — только `READY`, когда:
- P0/P1 `VERIFIED`;
- compose поднимается с нуля;
- tests/E2E green;
- privacy tests green;
- responsive screenshots есть;
- реальные validation results есть;
- документация полная;
- demo reset и demo scenario проходят.
