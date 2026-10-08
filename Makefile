SHELL := /bin/bash
.PHONY: up down build logs ps verify screenshots doctor autonomous demo-reset resource-baseline local-ai-up

up:
	docker compose up -d
down:
	docker compose down
build:
	docker compose build
logs:
	docker compose logs --tail=200
ps:
	docker compose ps
verify:
	./agent/verify.sh
screenshots:
	./agent/capture-screenshots.sh
doctor:
	./agent/doctor.sh
autonomous:
	./agent/autopilot.sh
demo-reset:
	./scripts/demo-reset.sh
resource-baseline:
	./scripts/resource-baseline.sh
local-ai-up:
	./scripts/local-ai-profile.sh
