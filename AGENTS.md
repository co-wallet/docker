# AGENTS.md

Инструкции по работе с Docker-репозиторием **co-wallet**.

## Назначение

Репозиторий содержит production- и development-конфигурацию всего стека. Compose использует родительскую директорию как общий build context и ожидает в ней каталоги `backend`, `frontend` и `docker`.

## Команды

```bash
make dev              # запустить dev-стек; первый запуск соберёт отсутствующие образы
make dev-build        # явно собрать оба dev-образа и запустить стек
make dev-down         # остановить dev-стек без удаления данных
make dev-logs         # следить за логами backend и frontend
make dev-status       # показать состояние сервисов

make deps-backend     # обновить Go-модули в постоянном cache volume
make deps-frontend    # выполнить npm ci в постоянном node_modules volume
make restart-backend  # перезапустить процесс, например после новой миграции
make recreate-backend # пересоздать backend после изменения environment
make recreate-frontend # пересоздать frontend после изменения environment
make rebuild-backend  # пересобрать только dev-образ backend
make rebuild-frontend # пересобрать только dev-образ frontend
make rebuild-all      # пересобрать оба dev-образа
```

Production-стек по-прежнему управляется напрямую через `docker compose build`, `docker compose up -d`, `docker compose ps` и `docker compose logs -f backend`.

`docker compose down -v` удаляет базу данных. Не выполнять эту команду без явного подтверждения пользователя.

## Build context

Build context равен корню workspace (`..`). Все `COPY` в Dockerfile задаются относительно корня:

- `COPY backend/go.mod backend/go.sum ./`
- `COPY frontend/package*.json ./`

Не использовать пути вида `../backend/...` внутри Dockerfile.

## Архитектура

```text
browser -> frontend/nginx :3000
             |-- /       -> Vite static files
             `-- /api/*  -> backend :8080 -> PostgreSQL :5432
```

- `docker-compose.yml` — production-сборка, healthcheck БД и volume `postgres_data`.
- `docker-compose.dev.yml` — bind mounts исходников, Air и Vite HMR, открытые dev-порты и постоянные volumes для Go/npm-кэшей и `node_modules`.
- `Dockerfile.backend` — multi-stage Go 1.25 build и Alpine runtime.
- `Dockerfile.backend.dev` — Go 1.25 + совместимая закреплённая версия Air; версию Go держать синхронной с `backend/go.mod`.
- `Dockerfile.frontend` — Node 22 build и nginx runtime.
- `nginx.conf` — `/api` proxy, SPA fallback, gzip и cache headers.

## Переменные окружения

- Обязательные production-переменные: `POSTGRES_PASSWORD`, `JWT_SECRET`.
- `ADMIN_*` настраивают первого администратора.
- `APP_URL` используется в invite-ссылках.
- `APP_PORT`, `BACKEND_PORT` и `POSTGRES_PORT` задают host-порты dev-стека; backend по умолчанию доступен на `8081`, чтобы не конфликтовать с другими локальными сервисами.
- `SMTP_*` необязательны; без них ссылка показывается в интерфейсе.
- `.env` содержит секреты и никогда не коммитится.

## Проверка изменений

- Обычные изменения `.go`, `.ts`, `.tsx` и CSS подхватываются Air/Vite; образ не пересобирать.
- После изменения зависимостей использовать `make deps-backend` или `make deps-frontend`.
- После изменения переменных окружения пересоздавать только затронутый сервис.
- После изменения Dockerfile, версии runtime или системных пакетов пересобирать только затронутый dev-образ.
- Перед production-развёртыванием собирать production-образы полностью.
- Проверять dev-конфигурацию через `docker compose -f docker-compose.yml -f docker-compose.dev.yml config`.
- После запуска проверять `make dev-status` и при необходимости `make dev-logs`.
- Не удалять volumes, данные или backup-файлы без явного запроса пользователя.
