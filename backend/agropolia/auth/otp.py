from __future__ import annotations

import json
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from agropolia.config import Settings
from agropolia.errors import DomainError
from agropolia.security import otp_digest, secret_hash


@dataclass(slots=True)
class OtpRecord:
    digest: str
    expires_at: datetime


class OtpStore(ABC):
    @abstractmethod
    async def put(self, key: str, record: OtpRecord, ttl_seconds: int) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> OtpRecord | None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class AttemptLimiter(ABC):
    @abstractmethod
    async def hit(self, identifier: str, device_id: str) -> None: ...


class ResendLimiter(ABC):
    @abstractmethod
    async def acquire(self, key: str, ttl_seconds: int) -> None: ...


class InMemoryOtpStore(OtpStore):
    def __init__(self) -> None:
        self.records: dict[str, OtpRecord] = {}

    async def put(self, key: str, record: OtpRecord, ttl_seconds: int) -> None:
        self.records[key] = record

    async def get(self, key: str) -> OtpRecord | None:
        record = self.records.get(key)
        if record and record.expires_at <= datetime.now(timezone.utc):
            self.records.pop(key, None)
            return None
        return record

    async def delete(self, key: str) -> None:
        self.records.pop(key, None)


class InMemoryAttemptLimiter(AttemptLimiter):
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)
        self.hits: dict[str, list[datetime]] = {}

    async def hit(self, identifier: str, device_id: str) -> None:
        now = datetime.now(timezone.utc)
        for key in (f"identifier:{identifier}", f"device:{device_id}"):
            current = [ts for ts in self.hits.get(key, []) if now - ts < self.window]
            if len(current) >= self.limit:
                raise DomainError("RATE_LIMITED", "Слишком много попыток. Повторите позже", 429)
            current.append(now)
            self.hits[key] = current


class InMemoryResendLimiter(ResendLimiter):
    def __init__(self) -> None:
        self.until: dict[str, datetime] = {}

    async def acquire(self, key: str, ttl_seconds: int) -> None:
        now = datetime.now(timezone.utc)
        if self.until.get(key, now) > now:
            raise DomainError("OTP_RESEND_TOO_SOON", "Повторный запрос кода пока недоступен", 429)
        self.until[key] = now + timedelta(seconds=ttl_seconds)


class RedisOtpStore(OtpStore):
    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    async def put(self, key: str, record: OtpRecord, ttl_seconds: int) -> None:
        await self.redis.setex(key, ttl_seconds, json.dumps({"digest": record.digest, "expires_at": record.expires_at.isoformat()}))

    async def get(self, key: str) -> OtpRecord | None:
        raw = await self.redis.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return OtpRecord(digest=data["digest"], expires_at=datetime.fromisoformat(data["expires_at"]))

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)


class RedisResendLimiter(ResendLimiter):
    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    async def acquire(self, key: str, ttl_seconds: int) -> None:
        ok = await self.redis.set(key, "1", ex=ttl_seconds, nx=True)
        if not ok:
            raise DomainError("OTP_RESEND_TOO_SOON", "Повторный запрос кода пока недоступен", 429)


_RATE_LIMIT_LUA = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
for i,key in ipairs(KEYS) do
  redis.call('ZREMRANGEBYSCORE', key, '-inf', now-window)
  if redis.call('ZCARD', key) >= limit then
    return 0
  end
end
for i,key in ipairs(KEYS) do
  redis.call('ZADD', key, now, member .. ':' .. i)
  redis.call('EXPIRE', key, math.ceil(window/1000))
end
return 1
"""


class RedisAttemptLimiter(AttemptLimiter):
    def __init__(self, redis_client, limit: int, window_seconds: int) -> None:
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds

    async def hit(self, identifier: str, device_id: str) -> None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        member = f"{now_ms}:{secrets.token_hex(6)}"
        ok = await self.redis.eval(
            _RATE_LIMIT_LUA,
            2,
            f"otp:attempts:identifier:{secret_hash(identifier)[:40]}",
            f"otp:attempts:device:{secret_hash(device_id)[:40]}",
            now_ms,
            self.window_seconds * 1000,
            self.limit,
            member,
        )
        if not ok:
            raise DomainError("RATE_LIMITED", "Слишком много попыток. Повторите позже", 429)


class OtpService:
    def __init__(self, settings: Settings, store: OtpStore, limiter: AttemptLimiter, resend_limiter: ResendLimiter, provider) -> None:
        self.settings = settings
        self.store = store
        self.limiter = limiter
        self.resend_limiter = resend_limiter
        self.provider = provider

    @staticmethod
    def key(method: str, identifier: str, device_id: str, purpose: str) -> str:
        return f"otp:{secret_hash(f'{method}|{purpose}|{identifier}|{device_id}')[:40]}"

    @staticmethod
    def resend_key(method: str, identifier: str, purpose: str) -> str:
        return f"otp:resend:{secret_hash(f'{method}|{purpose}|{identifier}')[:40]}"

    async def request(self, method: str, identifier: str, device_id: str, purpose: str) -> str:
        await self.resend_limiter.acquire(
            self.resend_key(method, identifier, purpose),
            self.settings.otp_resend_cooldown_seconds,
        )
        code = self.settings.dev_otp_code if self.settings.env in {"development", "test"} else f"{secrets.randbelow(1_000_000):06d}"
        record = OtpRecord(
            digest=otp_digest(self.settings.otp_secret, method, identifier, device_id, purpose, code),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.settings.otp_ttl_seconds),
        )
        await self.store.put(self.key(method, identifier, device_id, purpose), record, self.settings.otp_ttl_seconds)
        await self.provider.deliver(identifier, code, self.settings.otp_ttl_seconds)
        return code

    async def verify(self, method: str, identifier: str, device_id: str, purpose: str, code: str) -> None:
        await self.limiter.hit(identifier, device_id)
        key = self.key(method, identifier, device_id, purpose)
        record = await self.store.get(key)
        if record is None:
            raise DomainError("OTP_EXPIRED", "Код истёк или не был запрошен", 400)
        digest = otp_digest(self.settings.otp_secret, method, identifier, device_id, purpose, code)
        if not __import__("hmac").compare_digest(digest, record.digest):
            raise DomainError("OTP_INVALID", "Неверный код", 400)
        await self.store.delete(key)
