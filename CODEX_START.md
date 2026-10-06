# Стартовый запрос для интерактивного Codex

Из корня репозитория:

```bash
codex
```

После запуска вставь:

```text
Работай как lead engineer проекта FSP Talent Platform.

Следуй AGENTS.md, исходному ТЗ и docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md.
Цель — довести target scope из docs/REQUIREMENTS_MATRIX.md до VERIFIED через внешний supervisor.

Сначала:
1. Проверь текущее состояние репозитория.
2. Прочитай conference clarifications, .agent/BACKLOG.md, docs/PRODUCT_SPEC.md и документы ближайшего незавершённого milestone.
3. Сверь backlog с новыми требованиями: уникальные assessment forms, anti-AI-by-design, employer hiring pipeline/tasks, minor consent documents, .ru-only registration, working Keycloak demo, FSP achievement ranking, ProofMatch, post-match chat, CPU/no-GPU and load testing.
4. Актуализируй .agent/STATUS.md и при необходимости создай ExecPlan.
5. Реализуй один ближайший coherent end-to-end milestone или крупный кусок milestone.
6. Добавь тесты и evidence.
7. Не объявляй VERIFIED самостоятельно.

Не спрашивай о технических деталях, которые можешь безопасно решить сам.
При выборе между декоративным решением и проверяемой бизнес-логикой выбирай бизнес-логику, но UI должен оставаться современным, FSP-branded и responsive.

Нельзя использовать GPU как обязательную зависимость. Core обязан работать при LOCAL_AI_ENABLED=false.
Нельзя использовать AI-detector как автоматическое основание для провала кандидата.

После рабочего блока дай краткий итог: что реализовано, requirement IDs, тесты, что проверить supervisor.
```

Полный автономный режим:

```bash
./agent/autopilot.sh
```
