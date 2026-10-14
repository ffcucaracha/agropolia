import pytest

from agropolia.auth.otp import (
    InMemoryAttemptLimiter,
    InMemoryOtpStore,
    InMemoryResendLimiter,
    OtpService,
)
from agropolia.config import Settings
from agropolia.errors import DomainError
from agropolia.integrations.email import DevelopmentEmailOtpProvider


def service():
    settings = Settings(env="development", dev_otp_code="123456", otp_resend_cooldown_seconds=60)
    return OtpService(
        settings,
        InMemoryOtpStore(),
        InMemoryAttemptLimiter(5, 900),
        InMemoryResendLimiter(),
        DevelopmentEmailOtpProvider(),
    )


@pytest.mark.asyncio
async def test_otp_is_one_time():
    otp = service()
    await otp.request("email", "user@example.test", "device-0001", "login")
    await otp.verify("email", "user@example.test", "device-0001", "login", "123456")
    with pytest.raises(DomainError) as exc:
        await otp.verify("email", "user@example.test", "device-0001", "login", "123456")
    assert exc.value.code == "OTP_EXPIRED"


@pytest.mark.asyncio
async def test_otp_attempt_limit():
    otp = service()
    await otp.request("email", "user@example.test", "device-0001", "login")
    for _ in range(5):
        with pytest.raises(DomainError) as exc:
            await otp.verify("email", "user@example.test", "device-0001", "login", "000000")
        assert exc.value.code == "OTP_INVALID"
    with pytest.raises(DomainError) as exc:
        await otp.verify("email", "user@example.test", "device-0001", "login", "000000")
    assert exc.value.code == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_resend_cooldown():
    otp = service()
    await otp.request("email", "user@example.test", "device-0001", "login")
    with pytest.raises(DomainError) as exc:
        await otp.request("email", "user@example.test", "device-0001", "login")
    assert exc.value.code == "OTP_RESEND_TOO_SOON"


class FailingEmailProvider:
    async def deliver(self, email: str, code: str, ttl_seconds: int) -> None:
        raise RuntimeError("smtp unavailable")


@pytest.mark.asyncio
async def test_delivery_failure_releases_challenge_and_resend_cooldown():
    settings = Settings(
        env="development",
        dev_otp_code="123456",
        otp_resend_cooldown_seconds=60,
    )
    store = InMemoryOtpStore()
    resend = InMemoryResendLimiter()
    otp = OtpService(
        settings,
        store,
        InMemoryAttemptLimiter(5, 900),
        resend,
        FailingEmailProvider(),
    )

    with pytest.raises(DomainError) as exc:
        await otp.request(
            "email",
            "delivery@example.test",
            "device-delivery",
            "login",
        )
    assert exc.value.code == "OTP_DELIVERY_FAILED"

    # A failed delivery must not consume the resend window.
    with pytest.raises(DomainError) as second:
        await otp.request(
            "email",
            "delivery@example.test",
            "device-delivery",
            "login",
        )
    assert second.value.code == "OTP_DELIVERY_FAILED"


@pytest.mark.asyncio
async def test_new_challenge_replaces_previous_device_challenge():
    settings = Settings(
        env="development",
        dev_otp_code="123456",
        otp_resend_cooldown_seconds=60,
    )
    store = InMemoryOtpStore()
    resend = InMemoryResendLimiter()
    otp = OtpService(
        settings,
        store,
        InMemoryAttemptLimiter(5, 900),
        resend,
        DevelopmentEmailOtpProvider(),
    )
    identifier = "replace@example.test"
    purpose = "login"

    await otp.request("email", identifier, "device-old", purpose)
    await resend.release(otp.resend_key("email", identifier, purpose))
    await otp.request("email", identifier, "device-new", purpose)

    with pytest.raises(DomainError) as exc:
        await otp.verify(
            "email",
            identifier,
            "device-old",
            purpose,
            "123456",
        )
    assert exc.value.code == "OTP_INVALID"

    await otp.verify(
        "email",
        identifier,
        "device-new",
        purpose,
        "123456",
    )
