# I-0 — границы нулевой итерации и план реализации

**Статус:** рабочая спецификация итерации  
**Дата:** 2026-10-01  
**Основание:** ФТЗ «Агрополия» v1.0 от 23.09.2026 и `docs/ftz-architecture-amendments-2026-10-01.md`

---

## 1. Назначение I-0

Нулевая итерация создаёт production-oriented каркас нового проекта «Агрополия» и первый рабочий вертикальный сценарий:

```text
запуск приложения
  -> стартовый экран
  -> регистрация или вход по телефону
  -> создание базового пользовательского/организационного контекста
  -> авторизованная зона
  -> минимальный dashboard
```

Главная цель I-0 — не реализация продуктовых модулей MVP, а проверка и фиксация фундамента, на котором они будут строиться дальше:

- инфраструктура локальной разработки;
- Docker-based deployment units;
- backend как модульный монолит;
- frontend из общей React/TypeScript-кодовой базы;
- PostgreSQL/PostGIS;
- Redis;
- NATS JetStream;
- базовая аутентификация и сессии;
- базовая модель `User -> Membership -> Organization`;
- серверная авторизация и tenant isolation;
- transactional outbox/inbox foundation;
- серверная политика поддерживаемых версий клиента;
- CI и обязательные security/integration tests;
- технический spike Capacitor до начала основной mobile-разработки.

I-0 должна завершиться работающим приложением, а не только структурой репозитория или набором документов.

---

## 2. Важное терминологическое уточнение

### 2.1. Стартовый экран — не onboarding

В I-0 **не реализуется продуктовый onboarding из FR-AUTH-04**.

Под стартовым экраном понимается первый экран незалогиненного мобильного приложения, который:

- идентифицирует продукт «Агрополия»;
- кратко объясняет назначение приложения;
- предлагает два явных действия:
  - **Войти**;
  - **Зарегистрироваться**.

Стартовый экран не должен:

- имитировать персональную ценность по полям;
- показывать демо-поля;
- предлагать настройку дайджеста;
- считать сценарий `onboarding_completed`;
- заменять будущий onboarding FR-AUTH-04.

Полноценный onboarding из ФТЗ будет реализован позже, когда появятся данные `FIELD + METEO + NOTIF`.

---

## 3. Функциональные границы I-0

### 3.1. Стартовый экран мобильного приложения

В scope:

- экран для неавторизованного пользователя;
- логотип/название продукта и краткое описание;
- переход в сценарий входа;
- переход в сценарий регистрации;
- корректное поведение при уже существующей валидной сессии: пользователь сразу попадает в авторизованную часть приложения.

Экран является частью общей клиентской кодовой базы и должен корректно работать в mobile shell через Capacitor.

### 3.2. Вход по номеру телефона

I-0 реализует основу FR-AUTH-01 и NFR-SEC-03:

- ввод номера телефона;
- запрос OTP;
- OTP действует 5 минут;
- не более 5 попыток за 15 минут на номер и устройство;
- успешная проверка OTP создаёт пользовательскую сессию;
- выдаются access/refresh tokens;
- access token — 15 минут;
- refresh token — 30 дней;
- refresh token ротируется;
- сессия привязывается к устройству;
- logout отзывает текущую сессию;
- защита от перебора реализуется на backend.

В I-0 **не закрывается FR-AUTH-01 целиком**. Вне scope этой итерации:

- вход по биометрии/PIN устройства;
- полноценный пользовательский экран «Устройства»;
- UI для просмотра и отзыва всех отдельных сессий.

Архитектура хранения сессий должна позволять добавить эти возможности без изменения модели аутентификации.

### 3.3. Регистрация нового пользователя и хозяйства

I-0 реализует базовый путь нового хозяйства на основе FR-AUTH-03.

Минимальный сценарий:

```text
стартовый экран
  -> Зарегистрироваться
  -> телефон
  -> OTP
  -> имя пользователя
  -> данные хозяйства
  -> создание User
  -> создание Organization
  -> создание Membership(role=owner)
  -> dashboard
```

В первой итерации поддерживается регистрация нового хозяйства типов:

- СХО;
- КФХ.

Минимальные данные организации:

- тип;
- ИНН;
- название;
- контактный телефон — из подтверждённого номера пользователя.

Требования:

- ИНН валидируется по контрольному числу;
- ИНН должен быть уникален среди создаваемых хозяйств;
- пользователь, создавший организацию, получает membership с ролью `owner`;
- операция создания выполняется транзакционно;
- пользователь не должен оказаться в состоянии «создан User, но не создана Organization/Membership».

В I-0 не реализуются:

- INT-METEO-01 и связывание существующей учётной записи «Метеомониторинга»;
- автоматическая подстановка названия из ЕГРЮЛ/ЕГРИП;
- FR-ORG-04 «Запрос доступа к существующей организации»;
- регистрация партнёра;
- упрощённая регистрация ЛПХ;
- регистрация пасечника;
- верификация организации FR-AUTH-06.

Если ИНН уже существует, I-0 возвращает корректную доменную ошибку без создания дубля. Полный сценарий запроса доступа переносится в следующую итерацию, в которой будет закрываться FR-ORG-04.

### 3.4. Базовый организационный контекст

С первого дня используются сущности:

```text
User
Organization
Membership

User --< Membership >-- Organization
```

Это обязательный фундамент для дальнейшей ролевой модели ФТЗ.

В I-0:

- один пользователь может технически иметь несколько Membership;
- активная организация является частью авторизованного контекста;
- backend не доверяет `org_id` из payload;
- доступ к tenant-owned данным проверяется через membership и роль;
- роль `owner` реализуется как минимум для зарегистрировавшего хозяйство пользователя.

Полная матрица ролей FR-ORG-02 в I-0 не реализуется.

### 3.5. Согласие на обработку персональных данных

В I-0 реализуется только та часть FR-PRIV-01, которая требуется непосредственно для регистрации:

- отдельное согласие на обработку персональных данных;
- версия текста согласия;
- дата/время;
- канал;
- технический контекст устройства;
- IP в security/audit-контуре, если это допускается принятой моделью журналирования.

Согласия, относящиеся к ещё отсутствующим функциям, не запрашиваются заранее:

- геоданные полей/пасек;
- публикации в ленту;
- передача обезличенных запросов партнёрам;
- маркетинговые уведомления.

Они должны запрашиваться при первом использовании соответствующей функции, как предусмотрено ФТЗ.

### 3.6. Минимальный dashboard

После успешной регистрации или входа пользователь попадает на минимальный dashboard.

Правило I-0: **dashboard показывает только реально существующие данные**.

Разрешено показывать:

- имя пользователя;
- подтверждённый номер телефона в безопасном формате;
- название активной организации;
- тип организации;
- ИНН;
- текущую роль пользователя в организации.

Dashboard не содержит:

- моков;
- демо-данных;
- карточек будущих функций;
- пунктов «скоро»;
- фиктивной погоды;
- фиктивных полей;
- фиктивных задач;
- фиктивных уведомлений.

Если данных в системе ещё нет, соответствующего блока на dashboard быть не должно.

### 3.7. Выход и восстановление сессии

В scope:

- logout;
- восстановление валидной сессии после перезапуска приложения;
- refresh access token;
- корректное завершение сессии при отозванном/невалидном refresh token;
- очистка локального auth-state при logout.

---

## 4. Технические границы I-0

### 4.1. Backend

Backend создаётся как **модульный монолит на FastAPI**.

Минимальная структура:

```text
backend/
  auth/
  organizations/
  integrations/
  shared/
```

Границы модулей должны быть явными, даже если они развёртываются одним приложением.

В I-0 должны быть заложены:

- FastAPI application;
- Pydantic;
- SQLAlchemy 2;
- Alembic;
- единый формат ошибок по §9.4 ФТЗ;
- request/trace id;
- конфигурация окружения;
- health/readiness endpoints;
- OpenAPI как контракт API;
- dependency boundaries между модулями.

### 4.2. PostgreSQL/PostGIS

Используется один PostgreSQL cluster/database.

Минимальные схемы:

```text
auth.*
org.*
shared.*
```

PostGIS устанавливается сразу как часть целевой платформы, хотя геоданные в бизнес-сценарии I-0 ещё не используются.

Минимальные сущности:

```text
auth.user
auth.session

org.organization
org.membership
org.consent

shared.outbox_event
shared.inbox_event
```

Для доменных сущностей применяются соглашения ФТЗ:

- UUID v7;
- `created_at`;
- `updated_at`;
- `version`.

Миграции должны полностью поднимать схему с чистой БД.

### 4.3. Redis

Redis используется только для задач, согласованных архитектурными поправками:

- cache;
- rate limiting;
- краткоживущие distributed locks при обоснованной необходимости.

Для I-0 основной обязательный сценарий Redis — rate limiting OTP/auth.

Redis **не используется как task broker**.

### 4.4. NATS JetStream

NATS JetStream поднимается уже в I-0 как единая async-инфраструктура будущего MVP.

Celery и Arq не используются.

В I-0 требуется:

- NATS в Docker Compose;
- базовая конфигурация JetStream;
- Python infrastructure adapter/publisher;
- consumer infrastructure;
- проверка повторной доставки;
- идемпотентная обработка сообщения через inbox-механизм.

Полноценные продуктовые события из §9.6 ФТЗ в этой итерации не добавляются искусственно.

Работоспособность инфраструктуры проверяется integration test, который создаёт outbox-запись, публикует её в NATS и подтверждает идемпотентную обработку consumer.

### 4.5. Transactional outbox/inbox

В I-0 создаётся backend foundation из архитектурных поправок:

```text
PostgreSQL transaction
  |- domain changes
  '- outbox_event
          |
          v
   outbox publisher
          |
          v
     NATS JetStream
```

Обязательные свойства:

- событие не публикуется из request handler до commit транзакции;
- outbox publisher повторяет доставку до подтверждения;
- consumer использует `event_id`;
- повторная доставка не должна изменять результат;
- outbox/inbox доступны как shared infrastructure для будущих доменных модулей.

### 4.6. Frontend

Клиент создаётся на:

- React;
- TypeScript;
- Vite;
- актуальных поддерживаемых stable-версиях на момент начала реализации;
- версии фиксируются lockfile.

Минимальные клиентские области:

```text
/start
/auth/login
/auth/register
/app
```

Конкретная структура роутов может отличаться, но должны существовать:

- public shell;
- auth flow;
- protected application shell;
- API client;
- session state;
- route guards;
- error handling.

### 4.7. Capacitor и persistence abstraction

В I-0 создаётся Capacitor foundation для Android/iOS.

IndexedDB и SQLite рассматриваются как реализации общего persistence abstraction:

```text
Domain / application layer
        |
Repository interfaces
        |
Local persistence abstraction
        |
   +----+----+
   |         |
SQLite    IndexedDB
native      web
```

В I-0 не требуется полноценный offline sync engine, но запрещается строить клиентскую бизнес-логику на прямых platform checks.

### 4.8. Обязательный Capacitor technical spike

До завершения I-0 должен быть выполнен и задокументирован spike на целевых Android/iOS устройствах для проверки:

- background sync;
- push;
- SQLite;
- MapLibre;
- offline tiles;
- загрузка и докачка медиа;
- камера;
- GPS;
- secure storage;
- восстановление фоновых операций после OS kill.

Spike не означает production-реализацию этих функций.

Результат должен содержать:

- что проверено;
- на каких версиях ОС/устройствах;
- какие библиотеки использовались;
- известные ограничения;
- найденные риски;
- решения, которые требуют ADR.

### 4.9. Хранение auth credentials на клиенте

В native-приложении токены/ключевой материал хранятся через защищённое хранилище платформы — Keystore/Keychain.

Для web/PWA отдельно фиксируется безопасная стратегия хранения auth-state. Решение должно быть принято до завершения реализации auth и оформлено технической заметкой/ADR; refresh credential не должен без обоснования храниться в обычном `localStorage`.

### 4.10. Server-side client version policy

В I-0 реализуется принятая серверная политика версий мобильного клиента.

Конфигурация содержит отдельно для Android/iOS:

- `latest_version`;
- `recommended_version`;
- `minimum_supported_version`.

Клиент передаёт платформу и версию backend в стандартизованном client context.

Поведение:

- версия ниже `recommended_version`, но не ниже minimum — soft update state;
- версия ниже `minimum_supported_version` — forced update state.

Конкретные имена headers/endpoints фиксируются в OpenAPI/ADR I-0.

### 4.11. Безопасность и tenant isolation

I-0 должна сразу обеспечить следующие invariants:

- `org_id` защищённого ресурса определяется из авторизованного контекста;
- payload пользователя не является доверенным источником tenant identity;
- доступ к tenant-owned данным проверяет membership;
- горизонтальная межорганизационная эскалация запрещена;
- приватные DTO не должны случайно становиться публичными DTO;
- operational logs не содержат ПДн;
- security/audit logs отделены от operational logs;
- секреты не коммитятся в репозиторий;
- production-подход к encryption at rest и key management документирован согласно архитектурным поправкам.

RLS в PostgreSQL может быть рассмотрен отдельно как defense-in-depth; его включение в I-0 не является обязательным без отдельного ADR.

### 4.12. Docker и локальная среда

Из чистого checkout разработчик должен иметь возможность поднять проект стандартизованной командой через Docker Compose.

Минимальный состав:

```text
client
backend-api
backend-worker
postgres + postgis
redis
nats
```

API и worker могут собираться из одного backend image с разными entrypoint.

Kubernetes в I-0 не используется.

### 4.13. CI

Каждый PR должен как минимум проверять:

- backend tests;
- frontend tests;
- lint/static analysis;
- TypeScript typecheck;
- миграции БД;
- build frontend;
- build backend Docker image;
- integration tests критического auth flow;
- security tests tenant isolation;
- отсутствие известных проблем зависимостей в рамках выбранного CI tooling.

Конкретный CI provider определяется конфигурацией репозитория; application layer не должен зависеть от него.

---

## 5. Связь с требованиями ФТЗ

I-0 намеренно не является завершением всего модуля AUTH.

В рамках итерации закладываются или частично реализуются:

- FR-AUTH-01 — частично;
- FR-AUTH-03 — частично;
- FR-ORG-02 — foundation;
- FR-PRIV-01 — часть, относящаяся к регистрации;
- NFR-PLT-01 — foundation + technical spike;
- NFR-SEC-03 — auth/session foundation;
- NFR-SEC-04 — tenant isolation foundation;
- NFR-SEC-05 — secrets/key-management foundation;
- NFR-SEC-08 — secure client storage foundation;
- NFR-SEC-09 — разделение operational/security logs;
- NFR-MNT-03 — CI foundation;
- NFR-MNT-04 — базовая документация;
- архитектурные поправки №1, 3–8, 10, 12–17 в применимой к I-0 части.

Не следует закрывать FR/NFR как полностью выполненные, если их критерии приёмки выходят за фактический scope I-0.

---

## 6. Явно вне scope I-0

В I-0 не реализуются:

- FR-AUTH-02 / интеграция с «Метеомониторингом»;
- полноценный onboarding FR-AUTH-04;
- FR-AUTH-05;
- FR-AUTH-06;
- приглашения;
- запрос доступа к существующей организации;
- полная ролевая модель;
- поля и карточка поля;
- импорт KML/KMZ/GeoJSON;
- бизнес-логика PostGIS;
- карты как продуктовая функция;
- offline outbox клиента;
- sync engine FR-OFFLINE-*;
- наблюдения;
- ML;
- задачи;
- уведомления;
- дайджест;
- community/feed/QA;
- market/leads/partner;
- compliance/BEE/SATURN;
- bots;
- admin UI;
- продуктовая аналитика;
- объектное хранилище и production media workflow;
- реальные push-интеграции;
- реальный SMS provider;
- ClickHouse;
- Kubernetes.

Интерфейсы провайдеров могут быть предусмотрены там, где это необходимо для архитектуры, но внешние интеграции не должны блокировать завершение I-0.

---

## 7. Пошаговый план выполнения

### Шаг 0. Зафиксировать bootstrap-решения

Создать минимальный набор технических заметок/ADR для решений, которые должны быть одинаково поняты до кода:

1. структура modular monolith;
2. PostgreSQL schemas;
3. auth/session model;
4. token storage web/native;
5. NATS + transactional outbox/inbox;
6. client persistence abstraction;
7. server-side client version policy.

**Результат:** разработчик и AI-агент не принимают эти решения заново во время реализации.

---

### Шаг 1. Создать базовую структуру репозитория

Подготовить каталоги frontend/backend/infra/tests/docs в соответствии с актуальной архитектурой проекта.

Минимально:

```text
apps/
  client/

backend/
  auth/
  organizations/
  integrations/
  shared/

infra/

tests/
  integration/
  security/
```

**Результат:** проект имеет стабильные границы для дальнейших модулей.

---

### Шаг 2. Поднять локальную инфраструктуру

Добавить Docker Compose:

- PostgreSQL + PostGIS;
- Redis;
- NATS JetStream;
- backend API;
- backend worker;
- frontend dev/build target.

Добавить:

- env example;
- health checks;
- volumes;
- dependency ordering только там, где это действительно требуется;
- README с одной стандартной последовательностью запуска.

**Проверка:** новый checkout поднимается без ручной настройки инфраструктуры.

---

### Шаг 3. Реализовать backend skeleton

Создать:

- FastAPI application factory;
- settings/config;
- DB session/transaction management;
- единый error format;
- request id / trace context;
- health/live;
- health/ready;
- OpenAPI foundation.

**Проверка:** API стартует, readiness проверяет критические зависимости.

---

### Шаг 4. Создать БД и миграции foundation

Создать Alembic migrations для:

- schemas `auth`, `org`, `shared`;
- User;
- Session;
- Organization;
- Membership;
- Consent;
- OutboxEvent;
- InboxEvent.

Добавить необходимые unique constraints и индексы.

**Проверка:** миграции проходят на чистой БД и повторно не требуют ручных действий.

---

### Шаг 5. Реализовать OTP и session lifecycle

Реализовать auth use cases:

1. запрос OTP;
2. rate limit;
3. TTL кода;
4. проверка OTP;
5. выдача access/refresh;
6. refresh rotation;
7. device binding;
8. logout/revoke;
9. восстановление сессии.

Для I-0 используется dev OTP provider.

Внешний SMS provider скрывается за интерфейсом и не подключается.

**Тесты:**

- OTP истёк;
- неверный OTP;
- 5 попыток / 15 минут;
- повторное использование OTP;
- refresh rotation;
- revoked refresh;
- session/device mismatch.

---

### Шаг 6. Реализовать регистрацию хозяйства

После подтверждения телефона:

- создать/заполнить User;
- принять согласие ПДн;
- валидировать ИНН;
- проверить уникальность ИНН;
- создать Organization;
- создать Membership(role=owner);
- завершить транзакцию;
- вернуть авторизованный контекст.

**Тесты:**

- успешная регистрация;
- невалидный ИНН;
- дублирующий ИНН;
- rollback всей операции при ошибке;
- membership owner существует после регистрации.

---

### Шаг 7. Реализовать tenant/auth context backend

Добавить общий механизм:

- current user;
- current session;
- active organization;
- membership;
- role;
- server-side permission check.

Добавить security tests для межорганизационной изоляции.

**Проверка:** пользователь одной организации не может получить закрытый ресурс другой организации путём подмены идентификатора.

---

### Шаг 8. Создать frontend foundation

Настроить:

- React + TypeScript + Vite;
- router;
- API client;
- auth state;
- protected routes;
- public layout;
- authenticated layout;
- единый error handling;
- runtime configuration.

**Результат:** UI готов к подключению auth flow без временной архитектуры.

---

### Шаг 9. Реализовать стартовый экран

Сделать первый экран мобильного приложения:

- название/идентификация продукта;
- краткое описание;
- «Войти»;
- «Зарегистрироваться».

Без onboarding-механики и без демо-данных.

**Проверка:** пользователь с валидной сессией не попадает на start screen повторно.

---

### Шаг 10. Реализовать UI входа и регистрации

Подключить реальные backend endpoints:

**Вход:**

```text
phone -> OTP -> dashboard
```

**Регистрация:**

```text
phone -> OTP -> user/org data -> consent -> dashboard
```

Обработать доменные ошибки, включая duplicate INN.

**Проверка:** UI не использует mocked auth responses.

---

### Шаг 11. Реализовать минимальный dashboard

Dashboard получает данные только с backend.

Показывает только существующий:

- user;
- organization;
- membership/role.

Никаких future feature cards.

**Проверка:** данные после регистрации совпадают с сохранёнными в PostgreSQL.

---

### Шаг 12. Подключить NATS и outbox/inbox

Реализовать:

- outbox publisher;
- NATS connection;
- JetStream stream/consumer configuration;
- inbox deduplication;
- graceful restart/reconnect.

Не вводить новые бизнес-события только ради демонстрации.

**Integration test:**

```text
outbox row
  -> publisher
  -> NATS
  -> consumer
  -> inbox
  -> duplicate delivery
  -> side effect occurs once
```

---

### Шаг 13. Реализовать server-side client version policy

Создать серверную конфигурацию:

```json
{
  "android": {
    "latest_version": "...",
    "recommended_version": "...",
    "minimum_supported_version": "..."
  },
  "ios": {
    "latest_version": "...",
    "recommended_version": "...",
    "minimum_supported_version": "..."
  }
}
```

Клиент:

- передаёт platform/version;
- обрабатывает soft update;
- обрабатывает forced update.

**Проверка:** изменение policy не требует новой сборки backend/client code.

---

### Шаг 14. Выполнить Capacitor technical spike

Проверить весь список из архитектурных поправок:

- Android;
- iOS;
- background sync;
- push;
- SQLite;
- MapLibre;
- offline tiles;
- media upload/resume;
- camera;
- GPS;
- secure storage;
- OS kill / recovery.

Зафиксировать результаты отдельным документом/ADR.

**Проверка:** до начала I-1 известны ограничения платформы и нет скрытой зависимости от неподтверждённой возможности Capacitor.

---

### Шаг 15. Настроить CI

CI должен автоматически выполнять проверки из §4.13.

Отдельно должны быть видимыми failures для:

- migration failure;
- auth integration test;
- tenant isolation;
- frontend typecheck/build;
- backend tests.

---

### Шаг 16. Финальный e2e I-0

Обязательный демонстрационный сценарий:

```text
clean checkout
  -> docker compose up
  -> migrations
  -> открыть mobile/web client
  -> стартовый экран
  -> регистрация
  -> OTP
  -> создать хозяйство
  -> dashboard с реальными данными
  -> logout
  -> login
  -> dashboard
```

Дополнительно:

```text
outbox
  -> NATS JetStream
  -> consumer
  -> duplicate delivery
  -> idempotent result
```

И отдельно должен быть завершён Capacitor spike.

---

## 8. Definition of Done I-0

I-0 считается завершённой, если одновременно выполнены все условия:

1. проект поднимается из чистого checkout по задокументированной процедуре;
2. frontend/backend/DB/Redis/NATS запускаются в локальной Docker-среде;
3. пользователь видит стартовый экран;
4. новый пользователь может зарегистрировать СХО/КФХ;
5. существующий пользователь может войти по OTP;
6. auth/session lifecycle работает без mock backend;
7. пользователь после входа попадает на dashboard;
8. dashboard показывает только реальные данные User/Organization/Membership;
9. logout и session recovery работают;
10. tenant isolation покрыта automated security tests;
11. migrations воспроизводимы на чистой БД;
12. transactional outbox/inbox + NATS проверены integration test;
13. server-side mobile version policy работает;
14. Capacitor technical spike выполнен и задокументирован;
15. CI выполняет обязательный набор проверок;
16. OpenAPI и техническая документация соответствуют фактической реализации;
17. в I-0 не внесены скрытые реализации будущих продуктовых модулей и не используются демо-данные как часть production UI.

---

## 9. Что должно стать входом в I-1

После I-0 кодовая база должна позволять начинать следующую итерацию без переделки auth/infrastructure foundation.

Естественный следующий вертикальный срез:

- catalog foundation;
- field domain;
- INT-METEO contracts/adapters;
- реальные поля пользователя;
- первый полезный экран на реальных данных хозяйства.

Конкретные границы I-1 определяются отдельно и не являются частью данного документа.
