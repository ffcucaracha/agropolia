# ADR-0007: Server-side client version policy

Статус: принято.

Backend хранит per-platform `latest_version`, `recommended_version`, `minimum_supported_version`. Клиент передаёт `X-Client-Platform` и `X-Client-Version`. Endpoint `/api/v1/config/client-version` возвращает `ok`, `soft_update` или `force_update`. Значения конфигурируются окружением без изменения кода клиента.
