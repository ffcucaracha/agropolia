# ADR-0005: NATS JetStream + transactional outbox/inbox

Статус: принято.

Доменная транзакция пишет состояние и `shared.outbox_events`. Отдельный worker публикует событие после commit в JetStream. Consumer фиксирует `event_id + consumer` в `shared.inbox_events` в той же транзакции, что и side effect. Celery/Arq и Redis-broker не используются.
