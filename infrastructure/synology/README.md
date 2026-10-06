# Synology

Основная инструкция: `docs/SETUP_SYNOLOGY_CODEX_RU.md`.

Рекомендуется:
- отдельный non-admin user;
- проект `/volume1/docker/fsp-platform`;
- никаких Docker socket mounts в app containers;
- сначала работа только в LAN;
- reverse proxy/TLS после стабилизации;
- Task Scheduler для фонового supervisor.
