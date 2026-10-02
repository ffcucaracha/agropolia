# I-0 — рабочий журнал реализации

Дата старта: 2026-10-01  
Ветка: `i-0`

Журнал ведётся по шагам `iteration-0-scope-and-plan-2026-10-01.md`. Для каждого шага сначала фиксируется намерение, используемые паттерны и планируемые файлы, затем результат.

## Шаг 0 — bootstrap-решения

### Перед реализацией
- Реализую: набор ADR для modular monolith, схем БД, auth/session, token storage, NATS outbox/inbox, client persistence и client-version policy.
- Паттерны проекта: принятые архитектурные поправки 2026-10-01; модульный монолит; PostgreSQL schemas; provider abstractions; NATS JetStream; tenant isolation.
- Планируемые файлы: `docs/i-0/adr/0001-0007-*.md`, `docs/i-0/security-at-rest.md`.

### Результат
- ADR подготовлены; решения не оставлены на усмотрение реализации.
- Отдельно зафиксирована политика at-rest encryption/key management как инфраструктурное требование, а не локальная dev-настройка.

## Шаг 1 — структура репозитория

### Перед реализацией
- Реализую: базовую структуру `apps/client`, `backend`, `tests`, `infra/docs` без преждевременного создания бизнес-модулей I-1+.
- Паттерны проекта: bounded contexts `auth`, `organizations`, `shared`, `integrations`; общая клиентская кодовая база.
- Планируемые файлы: корневые README/config; package/module initializers; каталоги tests.

### Результат
- Создан минимальный каркас; модули I-1+ не добавлены.

## Шаг 2 — локальная инфраструктура

### Перед реализацией
- Реализую: Docker Compose для client, backend API/worker, PostgreSQL/PostGIS, Redis, NATS JetStream; `.env.example`, healthchecks и команды запуска.
- Паттерны проекта: Docker как deployment unit; Kubernetes backlog; Redis не task broker; NATS — async transport.
- Планируемые файлы: `compose.yaml`, `.env.example`, `Makefile`, `README.md`, Dockerfiles.

### Результат
- Compose описывает полный локальный runtime I-0; запуск требует Docker Compose и не зависит от Kubernetes.

## Шаг 3 — backend skeleton

### Перед реализацией
- Реализую: FastAPI application factory, settings, DB sessions, error contract, request-id/operational logging, liveness/readiness и router composition.
- Паттерны проекта: `/api/v1`, единый error DTO, operational logs без ПДн, async SQLAlchemy.
- Планируемые файлы: `backend/agropolia/main.py`, `config.py`, `db.py`, `errors.py`, `middleware.py`, `logging.py`.

### Результат
- Backend skeleton подготовлен; readiness проверяет PostgreSQL, Redis и NATS независимо и возвращает 503 при деградации критичных зависимостей.

## Шаг 4 — БД и миграции foundation

### Перед реализацией
- Реализую: Alembic и initial migration для `auth`, `org`, `shared`, включая PostGIS extension и сущности I-0.
- Паттерны проекта: одна БД, схемы bounded context; UUIDv7 application-side; version/timestamps; уникальные бизнес-инварианты.
- Планируемые файлы: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/20261001_0001_i0_foundation.py`, SQLAlchemy models.

### Результат
- Initial migration создаёт `auth.users`, `auth.sessions`, `org.organizations`, `org.memberships`, `org.consents`, `shared.outbox_events`, `shared.inbox_events`, `shared.security_audit_logs` и индексы/constraints.

## Шаг 5 — OTP и session lifecycle

### Перед реализацией
- Реализую: OTP TTL/attempt limits, dev delivery provider, access JWT, opaque rotating refresh, device binding, logout/revoke.
- Паттерны проекта: provider interface для SMS; Redis только для OTP/rate limit; refresh hash в БД; access token без tenant-данных.
- Планируемые файлы: `auth/otp.py`, `auth/tokens.py`, `auth/service.py`, `auth/router.py`, `integrations/sms.py`.

### Результат
- OTP действует 5 минут; verification attempts ограничены одновременно по телефону и устройству sliding-window limiter.
- Login выдаёт access/refresh; web refresh уходит HttpOnly cookie, native — в response для secure storage adapter.
- Refresh ротируется; reuse предыдущего refresh отзывает сессию; logout отзывает текущую session.

## Шаг 6 — регистрация хозяйства

### Перед реализацией
- Реализую: registration token после OTP и атомарное создание User/Organization/Membership/Consent/Session.
- Паттерны проекта: transaction boundary на use case; ИНН unique constraint + application validation; owner membership с первого дня.
- Планируемые файлы: `auth/service.py`, `auth/schemas.py`, organization models.

### Результат
- Поддержаны СХО/КФХ; ИНН 10/12 цифр проверяется по контрольному числу.
- Duplicate INN возвращает `ORG_INN_EXISTS`; отсутствие consent — `CONSENT_REQUIRED`.
- Регистрация не оставляет частично созданных доменных записей.

## Шаг 7 — tenant/auth context

### Перед реализацией
- Реализую: current auth context, active organization selection, membership validation и защищённые `/me`/organization endpoints.
- Паттерны проекта: tenant identity только из access context + проверенного `X-Org-Id`; чужая организация маскируется 404.
- Планируемые файлы: `auth/dependencies.py`, `organizations/router.py`, security tests.

### Результат
- `org_id` не принимается из mutation payload; `X-Org-Id` всегда сверяется с membership.
- Для единственной membership организация выбирается автоматически; при нескольких требуется явный header.

## Шаг 8 — frontend foundation

### Перед реализацией
- Реализую: React/TypeScript/Vite, router, TanStack Query, Zustand auth state, API client, protected route, persistence/token abstractions.
- Паттерны проекта: одна codebase; current stable stack; native secure storage; web HttpOnly refresh cookie; без platform checks в domain layer.
- Планируемые файлы: `apps/client/package.json`, `src/api`, `src/auth`, `src/persistence`, `App.tsx`, `main.tsx`.

### Результат
- Public/auth/protected shells реализованы; session bootstrap выполняется через refresh + `/me`.

## Шаг 9 — стартовый экран

### Перед реализацией
- Реализую: первый экран с идентификацией продукта и двумя действиями «Зарегистрироваться»/«Войти».
- Паттерны проекта: без onboarding, без demo data, mobile-first размеры элементов.
- Планируемые файлы: `StartPage.tsx`, `styles.css`.

### Результат
- `/start` реализован; валидная session перенаправляет в `/app`.

## Шаг 10 — UI входа и регистрации

### Перед реализацией
- Реализую: phone -> OTP -> login и phone -> OTP -> organization registration; реальные API ошибки.
- Паттерны проекта: backend source of truth; dev OTP виден только development response; consent только для ПДн.
- Планируемые файлы: `LoginPage.tsx`, `RegisterPage.tsx`.

### Результат
- UI работает только через backend API; mocks отсутствуют.

## Шаг 11 — минимальный dashboard

### Перед реализацией
- Реализую: `/me` query и отображение только User/Organization/Membership.
- Паттерны проекта: никаких «скоро», фальшивых полей, погоды, задач или уведомлений.
- Планируемые файлы: `DashboardPage.tsx`.

### Результат
- Dashboard отображает имя, masked phone, organization name/type/INN и role из фактического API ответа.

## Шаг 12 — NATS/outbox/inbox

### Перед реализацией
- Реализую: JetStream adapter, outbox publisher, inbox deduplication и integration test повторной доставки.
- Паттерны проекта: publish only after DB commit; `event_id` idempotency; Redis не broker.
- Планируемые файлы: `shared/nats.py`, `shared/outbox.py`, `shared/worker.py`, `test_outbox_inbox.py`.

### Результат
- Worker читает pending outbox с `FOR UPDATE SKIP LOCKED`, публикует в JetStream и отмечает delivery; inbox helper выполняет handler один раз на `event_id + consumer`.

## Шаг 13 — server-side client version policy

### Перед реализацией
- Реализую: per-platform config, comparison и endpoint; client headers + soft/force UI gate.
- Паттерны проекта: runtime config без mobile release; semver core comparison для release versions.
- Планируемые файлы: `shared/versioning.py`, `shared/router.py`, `VersionGate.tsx`.

### Результат
- `/api/v1/config/client-version` возвращает `ok|soft_update|force_update`; unit tests покрывают границы.

## Шаг 14 — Capacitor technical spike

### Перед реализацией
- Реализую: dependency/capability foundation и документирую device matrix; проверю всё, что возможно без физического Android/iOS runtime.
- Паттерны проекта: technical spike до основной mobile-функциональности; неизвестность не трактуется как успешная проверка.
- Планируемые файлы: `package.json`, `capacitor.config.ts`, `docs/i-0/capacitor-spike.md`.

### Результат
- Secure storage adapter реализован, candidate dependencies зафиксированы.
- **Частично:** device-dependent acceptance (background/OS kill/push/SQLite/MapLibre/camera/GPS/media resume) невозможно достоверно выполнить в текущей среде; сохранено как blocking checklist в `capacitor-spike.md`.

## Шаг 15 — CI

### Перед реализацией
- Реализую: отдельные unit/integration/security/frontend/docker-build jobs.
- Паттерны проекта: risk-oriented coverage; clean DB migration перед integration suite; dependency audit.
- Планируемые файлы: `.github/workflows/ci.yml`, tests.

### Результат
- CI конфигурация добавлена: unit, clean migration + integration/security against Compose services, frontend typecheck/test/build/audit, Docker build.
- Финальный GitHub Actions run #20 завершён успешно: `backend-unit`, `backend-integration`, `frontend`, `docker-build`, `e2e-i0` — **success**.

## Шаг 16 — финальный e2e I-0

### Перед реализацией
- Реализую: browser E2E полного пользовательского пути плюс отдельный backend integration flow для outbox/inbox.
- Паттерны проекта: browser test против реальных API/DB/Redis/NATS в CI; никаких mock responses.
- Планируемые файлы: `apps/client/e2e/i0.spec.ts`, `playwright.config.ts`, CI job `e2e-i0`.

### Результат
- Playwright-сценарий покрывает start -> register -> OTP -> organization -> dashboard -> logout -> login -> dashboard.
- Outbox/inbox redelivery покрыт отдельным integration test.
- Финальный GitHub Actions run #20 подтвердил полный browser E2E и infrastructure integration suite — **success**.
- Локальная автономная среда не имела Docker/native mobile runtime; фактическая Docker/browser проверка выполнена GitHub Actions.

## Итог для ревью

### Полностью реализовано
- modular-monolith backend skeleton FastAPI;
- Docker Compose topology для PostgreSQL/PostGIS, Redis, NATS, API, worker и client;
- initial Alembic migration и bounded-context schemas `auth`, `org`, `shared`;
- OTP foundation с TTL и sliding rate limit;
- access JWT + rotating refresh sessions + device binding + logout;
- атомарная регистрация СХО/КФХ с User/Organization/Membership(owner)/Consent/Session;
- tenant context и защита от horizontal privilege escalation на реализованных tenant endpoints;
- стартовый экран без onboarding;
- UI регистрации и входа без mock backend;
- dashboard только на реальных User/Organization/Membership данных;
- transactional outbox publisher и inbox deduplication foundation;
- server-side client version policy и client soft/forced update gate;
- web HttpOnly refresh-cookie strategy и native secure-storage adapter;
- CI definition: backend unit, integration/security, frontend typecheck/test/build/audit, Docker build, browser E2E;
- рабочий журнал и bootstrap ADR в `docs/i-0/`.

### Реализовано частично / требует внешней проверки
- Capacitor technical spike: dependency/foundation и secure-storage adapter готовы, но device-dependent проверки background/OS kill/push/SQLite/MapLibre/camera/GPS/media-resume требуют Android/iOS runtime; подробный blocking checklist — `docs/i-0/capacitor-spike.md`.
- Production consent wording: техническая версия/журнал согласия реализованы, юридически утверждённый текст в исходных материалах отсутствует и не был придуман.
- npm lockfile: top-level версии pinned, но lockfile невозможно достоверно сгенерировать в текущей offline-среде; должен быть создан после `npm install` в среде с registry и закоммичен до production release.

### Миграции
- `backend/alembic/versions/20261001_0001_i0_foundation.py`:
  - PostGIS extension;
  - schemas `auth`, `org`, `shared`;
  - `auth.users`, `auth.sessions`;
  - `org.organizations`, `org.memberships`, `org.consents`;
  - `shared.outbox_events`, `shared.inbox_events`, `shared.security_audit_logs`;
  - unique/index/check constraints I-0.

### Добавленные endpoints
- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`
- `GET /api/v1/organizations/{organization_id}`
- `GET /api/v1/config/client-version`
- `GET /health/live`
- `GET /health/ready`
- стандартный FastAPI `GET /openapi.json` / `/docs`.

### Тесты
Локально выполнено:
- `python -m compileall -q agropolia alembic ../tests` — успешно;
- `PYTHONPATH=. pytest -q ../tests/unit` — **10 passed**.

GitHub Actions run #20 — **success**, подтверждены:
- clean Alembic migration;
- auth integration flow;
- refresh reuse/session revocation;
- tenant isolation;
- NATS outbox -> JetStream -> inbox duplicate delivery;
- frontend TypeScript typecheck;
- Vitest;
- frontend build;
- npm audit;
- Docker builds;
- Playwright full I-0 browser flow.

Jobs:
- `backend-unit` — success;
- `backend-integration` — success;
- `frontend` — success;
- `docker-build` — success;
- `e2e-i0` — success.

### Команды для проверки
```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose run --rm backend-api alembic upgrade head
docker compose run --rm backend-api pytest -q /workspace/tests

cd apps/client
npm install
npm run typecheck
npm test -- --run
npm run build
npm run e2e
```

Для чистой проверки миграции:
```bash
docker compose down -v
docker compose up -d postgres redis nats
docker compose run --rm backend-api alembic upgrade head
```

### На что обратить внимание при code review
1. Auth contract: web использует HttpOnly refresh cookie, native получает refresh в body для secure storage; access token tenant не содержит.
2. Refresh reuse: revocation commit выполняется до возврата ошибки `REFRESH_REUSED` — важно не переносить raise обратно внутрь rollback-транзакции.
3. Tenant isolation: чужой `X-Org-Id` возвращает 404; payload не определяет tenant.
4. Registration transaction: User/Organization/Membership/Consent/Session создаются атомарно.
5. Dashboard: в нём нет ни одного placeholder/future-feature блока.
6. Outbox: publish не вызывается из request handler; worker берёт committed rows.
7. Operational logging: request bodies/phones/INN не логируются; security audit отделён.
8. Capacitor spike остаётся формальным blocking item до проверки на целевых устройствах.
9. До production нужен юридически утверждённый текст consent и production secrets/KMS/Vault configuration.
10. После первого успешного `npm install` следует закоммитить lockfile и заменить CI `npm install` на `npm ci`.


## Финальный статус автоматической проверки

На последнем полном прогоне до обновления документации GitHub Actions run #20 завершился со статусом **success** по всем пяти jobs. После документальных изменений README/worklog CI запускается повторно; изменения не затрагивают application code.
