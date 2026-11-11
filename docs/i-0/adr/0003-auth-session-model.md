# ADR-0003: OTP, access JWT и rotating refresh session

Статус: принято.

OTP подтверждает владение телефоном. Access JWT живёт 15 минут и содержит только технические идентификаторы `sub` и `sid`; tenant определяется server-side через membership. Refresh token — непрозрачный случайный секрет, в БД хранится SHA-256 hash. Refresh живёт 30 дней, ротируется; повтор предыдущего refresh приводит к отзыву сессии. Session привязана к `device_id`.
