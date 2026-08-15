# AGENTS.md

Инструкции для Codex при работе с Docker-репозиторием **co-wallet**.

## Назначение

Репозиторий содержит production- и development-конфигурацию всего стека. Соседние репозитории `../backend` и `../frontend` входят в общий build context, поэтому compose-команды запускаются только из этой директории.

## Команды

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f backend

# development с hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# остановка без удаления данных
docker compose down
```

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
- `docker-compose.dev.yml` — bind mounts исходников, Air и Vite HMR, открытые dev-порты.
- `Dockerfile.backend` — multi-stage Go 1.25 build и Alpine runtime.
- `Dockerfile.backend.dev` — Go 1.25 + Air; версию Go держать синхронной с `backend/go.mod`.
- `Dockerfile.frontend` — Node 22 build и nginx runtime.
- `nginx.conf` — `/api` proxy, SPA fallback, gzip и cache headers.

## Переменные окружения

- Обязательные production-переменные: `POSTGRES_PASSWORD`, `JWT_SECRET`.
- `ADMIN_*` настраивают первого администратора.
- `APP_URL` используется в invite-ссылках.
- `SMTP_*` необязательны; без них ссылка показывается в интерфейсе.
- `.env` содержит секреты и никогда не коммитится.

## Проверка изменений

- После изменений backend или frontend выполнять `docker compose build && docker compose up -d`.
- Проверять `docker compose ps` и `docker compose logs backend`.
- Для изменений compose проверять итоговую конфигурацию через `docker compose config`.
- Не удалять volumes, данные или backup-файлы без явного запроса пользователя.
