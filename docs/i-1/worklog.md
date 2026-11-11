# I-1 — рабочий журнал

Дата старта: 2026-11-11. Ветка: `i-1`, создана от актуального `main`.
Перед началом: сверены roadmap v1.1, ФТЗ v1.0, архитектурные поправки, I-0 ADR, backend/frontend и существующие тесты.
Код I-1 не меняется в `main`; решение о минимальном FR-FIELD-02 утверждено пользователем.

## Шаг 0 — спецификация
- Реализуется: границы первого web/PWA slice; отдельная документация `docs/i-1/`.
- Паттерны: modular monolith, Postgres schemas, authorized tenant context, optimistic concurrency, outbox/inbox.
- Файлы: `docs/i-1/scope-and-plan.md`, `docs/i-1/worklog.md`.
- Результат: план зафиксирован перед кодом.
- Blockers: INT-METEO-01…05, полный каталог, production legal consent, native testing.

## Шаг 1 — backend домены + миграции
План: Fields, Observations, Tasks, WorkLog, Notification, SyncOperation; DAL и API. Обязательные тесты: tenancy, состояния, идемпотентность, conflict.
Статус: в работе.

