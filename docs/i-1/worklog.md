# I-1 — рабочий журнал

Дата старта: 2026-11-11. Ветка `i-1`, основание `main@e4e6628d`. Код `main` не изменялся.
Scope и критерии: `docs/i-1/scope-and-plan.md`. Draft PR: https://github.com/ffcucaracha/agropolia/pull/5

## Шаг 0 — подготовка

- **Реализуется:** автономный web-first slice на реальных пользовательских данных; ограниченная часть `FR-FIELD-02` принята в scope.
- **FR:** `FR-FIELD-02/04/05` (части), `FR-OBS-01/02/05`, `FR-TASK-01/02/03/05/06/07`, `FR-OFFLINE-01/02/03/05`, `FR-NOTIF-01` (часть).
- **Паттерны:** modular monolith; одна PostgreSQL с bounded schemas; `TenantContext`; optimistic concurrency; NATS JetStream и transactional outbox/inbox; `LocalPersistence` abstraction.
- **Файлы:** `docs/i-1/scope-and-plan.md`, `docs/i-1/worklog.md`.
- **Результат:** выбор I-1 оформлен до кода; `i-1` создана от актуального `main`.

## Шаг 1 — доменная модель, API и миграции

- **Реализуется:** ручные поля без геометрии, приватные наблюдения, owner-only задачи, состояние выполнения, WorkLog, уведомления и синхронизация.
- **FR:** `FR-FIELD-02` (часть), `FR-OBS-01/02/05` (без full media/video/voice), `FR-TASK-01/02/03/05/06`, `FR-OFFLINE-02/03`.
- **Паттерны:** `TenantContext` из auth I-0; `org_id` из membership; чужие UUID маскируются 404; optimistic `base_version`; результат каждой `client_op_id` в PostgreSQL.
- **Файлы:** `backend/agropolia/workspace/{models,schemas,service,router}.py`, `backend/agropolia/main.py`, `backend/alembic/env.py`, `backend/alembic/versions/20261111_0003_i1_workspace.py`.
- **Результат:** `/api/v1/fields`, `/observations`, `/tasks`, `/work-log`, `/sync/ops`, `/sync/changes` работают через реальные SQLAlchemy entities. Зависимые offline записи могут использовать стабильно созданный клиентом UUID.
- **Тесты:** `tests/integration/test_i1_workspace.py`: создание/редактирование/изоляция field, observation, task lifecycle, work log, replay, conflict, cross-org ACL.

## Шаг 2 — web/PWA offline-first

- **Реализуется:** IndexedDB queue/cache, local optimistic projection, ordered submission, reconnect/visibility sync, конфликты с серверной версией, очередь ошибок.
- **FR:** web-часть `FR-OFFLINE-01/02/03/05`.
- **Паттерны:** интерфейс `LocalPersistence` I-0; `workspacePersistence` adapter; client `client_op_id` UUIDv7; server CAS и конфигурируемый retention `sync_idempotency_retention_days=30`.
- **Файлы:** `apps/client/src/persistence/{indexeddb,provider}.ts`, `apps/client/src/workspace/offline.ts`, `apps/client/src/auth/store.ts`, `backend/agropolia/workspace/{service,scheduler}.py`.
- **Результат:** поля/наблюдения/задачи сохраняются локально при отсутствии сети и синхронизируются позже. Client state partition by `userId:orgId`; logout очищает локальную базу с предупреждением о неотправленных изменениях.
- **Тесты:** серверная exactly-once / CAS / dependent operations в `test_i1_workspace.py`; browser offline/reconnect в `apps/client/e2e/i1.spec.ts`.
- **Особое исправление:** React StrictMode инициировал дублирующий refresh после перезагрузки и вызывал token-reuse revocation; добавлена single-flight защита в `apps/client/src/auth/store.ts`.

## Шаг 3 — пользовательские экраны и навигация

- **Реализуется:** «Сегодня», «Мои поля», создание/редактирование/карточка поля, наблюдения/журнал, задачи/карточка/выполнение, журнал работ, уведомления, настройки.
- **FR:** ограниченный набор выбранных Field/Obs/Task/Notif.
- **Паттерны:** React Router + TanStack Query + существующий Zustand auth store; никакой UI-заглушки погоды, рисков, AI, сообщества, рынка.
- **Файлы:** `apps/client/src/App.tsx`, `styles.css`, `workspace/{WorkspaceLayout,ui,FieldsPages,ObservationsPages,TasksPages,TodayAndNotifications,types}.tsx` и `.ts`.
- **Результат:** новые защищённые пользовательские routes; owner может создать поле, наблюдение, задачу и пройти весь task lifecycle. Хозяйство без полей получает реальное действие «Добавить поле».

## Шаг 4 — приватные фотографии

- **Реализуется:** upload JPEG/PNG/WebP, ограничение до 10, сжатие до 1.5 МБ JPEG, server ACL, клиентская очередь Blob в IndexedDB, отображение в приватной галерее, retry.
- **FR:** часть `FR-OBS-02`, `FR-TASK-06`.
- **Паттерны:** provider abstraction для object storage; dev local filesystem, production S3; авторизация и tenant ownership перед выдачей bytes; media UUID с идемпотентной регистрацией.
- **Файлы:** `backend/agropolia/workspace/{media,models}.py`, `backend/alembic/versions/20261111_0004_i1_media.py`, `backend/pyproject.toml`, `config.py`, `apps/client/src/workspace/{mediaQueue,MediaGallery}.tsx`/`.ts`, `apps/client/src/api/client.ts`.
- **Результат:** фото проходят через приватный backend, без общедоступного URL; геометки EXIF удаляются при обработке до появления утверждённого согласия на геоданные. Production требует private S3 credentials и подходящего размещения.
- **Тесты:** реальная загрузка, повтор с тем же ID, чтение JPEG, запрет чужому tenant.

## Шаг 5 — in-app уведомления

- **Реализуется:** центр уведомлений и настройка задач, task-created/status events → PostgreSQL outbox → NATS consumer → inbox → private Notification; durable task deadline scanner.
- **FR:** автономная часть `FR-TASK-07`, `FR-NOTIF-01`.
- **Паттерны:** NATS JetStream, transactional outbox/inbox, Postgres row-lock `SKIP LOCKED` для scheduler, серверное хранение `reminded_at`, no Redis broker.
- **Файлы:** `backend/agropolia/workspace/{notify_consumer,scheduler,models}.py`, `backend/agropolia/shared/worker.py`, `backend/alembic/versions/20261111_0005_i1_task_reminders.py`, `apps/client/src/workspace/TodayAndNotifications.tsx`.
- **Результат:** owner видит только свои in-app notifications; redelivery не дублирует, настройки доступны, срок задачи обрабатывается после worker restart.
- **Тесты:** `tests/integration/test_i1_workspace.py`, `test_i1_scheduler.py`.

## Шаг 6 — CI и приёмка

- **Реализуется:** реальные unit/integration/security/Playwright проверки; draft PR #5 остаётся unmerged.
- **Файлы:** `tests/integration/test_i1_workspace.py`, `tests/integration/test_i1_scheduler.py`, `apps/client/e2e/i1.spec.ts`.
- **Проверено:** на повторных запусках GitHub Actions успешно прошли backend-unit, backend-integration (на чистой PostgreSQL/PostGIS/Redis/NATS), frontend (TS typecheck, build, Vitest, audit), docker-build. GitHub Actions run [#43017195858](https://github.com/ffcucaracha/agropolia/actions/runs/43017195858) на commit `370ef2c893d46e3a2bbe953780ebb4082da9bebc` завершился **success** по всем пяти jobs, включая browser E2E I-0 + I-1 online + offline/reconnect. Причина прежней ошибки strict-mode refresh устранена single-flight bootstrap.
- **Осталось до продуктовой/production приёмки:** отдельное ревью интеграции медиа + offline на целевых браузерах/устройствах, утверждённые юридические согласия и конфигурация production S3. Проверки CI проходят, но production deployment не выполнялся.

## Не закрыто этим slice

- `INT-METEO-01…05`: внешние контракты отсутствуют; `FR-AUTH-02` и Meteo-dependent части `FR-FIELD-01/03/04/05/07`, `FR-NOTIF-02/03/04`.
- Полные `FR-FIELD-02` (KML/KMZ/контуры), `FR-OBS-02` (video/voice/STT/EXIF consent), `FR-OFFLINE-01/05` (native background/media + map cache), `FR-NOTIF-01` (push/бот/SMS), `FR-ORG-02/03` (staff), весь регулируемый контур/FR-TASK-04.
- Начальные справочники/погодные thresholds не подменялись неподтверждёнными данными.
- `main` не тронут; PR #5 draft, решение о merge отдельно.

## Финальное исправление изоляции клиентского кэша

После проверки повторного входа устранён риск переноса прежних tenant-owned React Query данных в новый пользовательский сеанс. На `setTokens/logout/bootstrap failure` очищается shared query cache; при выходе очищается и IndexedDB (с предупреждением о неотправленных операциях).

- Файлы: `apps/client/src/api/queryClient.ts`, `apps/client/src/main.tsx`, `apps/client/src/auth/store.ts`.
- Результат: в новом auth-контексте данные предыдущего пользователя не показываются из TanStack Query cache.
- Проверка: GitHub Actions run #43017195858 — полный зелёный прогон, включая browser flows.
