import pytest

from agropolia.auth.otp import InMemoryAttemptLimiter, InMemoryOtpStore, OtpService
from agropolia.config import Settings
from agropolia.errors import DomainError
from agropolia.integrations.sms import DevelopmentOtpProvider


@pytest.mark.asyncio
async def test_otp_is_one_time():
    settings = Settings(env="development", dev_otp_code="123456")
    service = OtpService(settings, InMemoryOtpStore(), InMemoryAttemptLimiter(5, 900), DevelopmentOtpProvider())
    await service.request("+79001234567", "device-0001", "login")
    await service.verify("+79001234567", "device-0001", "login", "123456")
    with pytest.raises(DomainError) as exc: await service.verify("+79001234567", "device-0001", "login", "123456")
    assert exc.value.code == "OTP_EXPIRED"


@pytest.mark.asyncio
async def test_otp_attempt_limit():
    settings = Settings(env="development", dev_otp_code="123456")
    service = OtpService(settings, InMemoryOtpStore(), InMemoryAttemptLimiter(5, 900), DevelopmentOtpProvider())
    await service.request("+79001234567", "device-0001", "login")
    for _ in range(5):
        with pytest.raises(DomainError) as exc: await service.verify("+79001234567", "device-0001", "login", "000000")
        assert exc.value.code == "OTP_INVALID"
    with pytest.raises(DomainError) as exc: await service.verify("+79001234567", "device-0001", "login", "000000")
    assert exc.value.code == "RATE_LIMITED"
