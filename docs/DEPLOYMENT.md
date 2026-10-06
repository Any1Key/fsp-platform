# Deployment

```bash
cp .env.example .env
# replace CHANGE_ME values
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Default:
- frontend `http://HOST:3000`
- Swagger `http://HOST:8000/docs`
- Keycloak `http://HOST:8081`
- Mailpit `http://HOST:8025`

Stop:
```bash
docker compose down
```

Logs:
```bash
docker compose logs -f --tail=200
```

Fresh destructive demo reset:
```bash
./scripts/demo-reset.sh
```

Do not expose bootstrap directly to the public Internet as production. Add TLS/reverse proxy, production
secrets, real SMTP, backups, monitoring and hardened identity before public deployment.
