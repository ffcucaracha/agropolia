from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

from agropolia.config import Settings


class EmailOtpProvider(Protocol):
    async def deliver(self, email: str, code: str, ttl_seconds: int) -> None: ...


class DevelopmentEmailOtpProvider:
    async def deliver(self, email: str, code: str, ttl_seconds: int) -> None:
        return None


class SmtpEmailOtpProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _send(self, email: str, code: str, ttl_seconds: int) -> None:
        message = EmailMessage()
        message["Subject"] = "Код входа в Агрополию"
        message["From"] = formataddr((self.settings.smtp_from_name, self.settings.smtp_from_email))
        message["To"] = email
        minutes = max(1, (ttl_seconds + 59) // 60)
        message.set_content(
            f"Ваш код: {code}\n\n"
            f"Код действует {minutes} мин.\n\n"
            "Если вы не запрашивали код, просто проигнорируйте это письмо."
        )
        smtp_cls = smtplib.SMTP_SSL if self.settings.smtp_ssl else smtplib.SMTP
        with smtp_cls(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as client:
            if self.settings.smtp_starttls and not self.settings.smtp_ssl:
                client.starttls()
            if self.settings.smtp_username:
                client.login(self.settings.smtp_username, self.settings.smtp_password or "")
            client.send_message(message)

    async def deliver(self, email: str, code: str, ttl_seconds: int) -> None:
        await asyncio.to_thread(self._send, email, code, ttl_seconds)
