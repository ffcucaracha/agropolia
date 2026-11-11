# ADR-0002: PostgreSQL schemas по bounded context

Статус: принято.

Один PostgreSQL cluster/database. I-0 использует схемы `auth`, `org`, `shared`. PostGIS включается сразу, но геодомен не создаётся до I-1. Межмодульные связи допускаются только через согласованные FK/сервисные функции; tenant identity не принимается из payload как доверенная.
