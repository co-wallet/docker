COMPOSE := docker compose
DEV_COMPOSE := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: dev dev-build dev-down dev-logs dev-status \
	restart-backend recreate-backend recreate-frontend \
	deps-backend deps-frontend rebuild-backend rebuild-frontend rebuild-all

dev:
	$(DEV_COMPOSE) up -d

dev-build:
	$(DEV_COMPOSE) up -d --build

dev-down:
	$(DEV_COMPOSE) down

dev-logs:
	$(DEV_COMPOSE) logs -f backend frontend

dev-status:
	$(DEV_COMPOSE) ps

restart-backend:
	$(DEV_COMPOSE) restart backend

recreate-backend:
	$(DEV_COMPOSE) up -d --force-recreate --no-deps backend

recreate-frontend:
	$(DEV_COMPOSE) up -d --force-recreate --no-deps frontend

deps-backend:
	$(DEV_COMPOSE) exec -T backend go mod download
	$(DEV_COMPOSE) restart backend

deps-frontend:
	$(DEV_COMPOSE) stop frontend
	$(DEV_COMPOSE) run --rm --no-deps frontend npm ci
	$(DEV_COMPOSE) up -d --no-deps frontend

rebuild-backend:
	$(DEV_COMPOSE) build backend
	$(DEV_COMPOSE) up -d --force-recreate --no-deps backend

rebuild-frontend:
	$(DEV_COMPOSE) build frontend
	$(DEV_COMPOSE) up -d --force-recreate --no-deps frontend

rebuild-all:
	$(DEV_COMPOSE) build
	$(DEV_COMPOSE) up -d
