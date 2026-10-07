from __future__ import annotations

from typing import Protocol


class OtpDeliveryProvider(Protocol):
    async def deliver(self, phone: str, code: str) -> None: ...


class DevelopmentOtpProvider:
    async def deliver(self, phone: str, code: str) -> None:
        # Deliberately no operational log with phone/code: both are sensitive.
        return None


class SmsOtpProvider:
    async def deliver(self, phone: str, code: str) -> None:
        raise NotImplementedError("INT-SMS-01 is outside I-0; configure a provider in a later iteration")
