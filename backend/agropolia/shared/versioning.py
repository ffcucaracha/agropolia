from __future__ import annotations

from dataclasses import dataclass

from agropolia.config import PlatformVersionPolicy, Settings
from agropolia.errors import DomainError


@dataclass(frozen=True, slots=True)
class ParsedVersion:
    parts: tuple[int, ...]

    @classmethod
    def parse(cls, value: str) -> "ParsedVersion":
        core = value.split("-", 1)[0].split("+", 1)[0]
        try:
            parts = tuple(int(part) for part in core.split("."))
        except ValueError as exc:
            raise DomainError("INVALID_CLIENT_VERSION", "Некорректная версия клиента", 400) from exc
        if not parts:
            raise DomainError("INVALID_CLIENT_VERSION", "Некорректная версия клиента", 400)
        return cls(parts=parts)

    def _pad(self, length: int) -> tuple[int, ...]:
        return self.parts + (0,) * (length - len(self.parts))

    def __lt__(self, other: "ParsedVersion") -> bool:
        length = max(len(self.parts), len(other.parts))
        return self._pad(length) < other._pad(length)


def evaluate_version(platform: str, version: str, settings: Settings) -> dict[str, str]:
    if platform not in settings.version_policies:
        raise DomainError("UNSUPPORTED_PLATFORM", "Неподдерживаемая платформа", 400)
    policy: PlatformVersionPolicy = settings.version_policies[platform]
    current = ParsedVersion.parse(version)
    minimum = ParsedVersion.parse(policy.minimum_supported_version)
    recommended = ParsedVersion.parse(policy.recommended_version)
    state = "force_update" if current < minimum else "soft_update" if current < recommended else "ok"
    return {"platform": platform, "current_version": version, "state": state, "latest_version": policy.latest_version, "recommended_version": policy.recommended_version, "minimum_supported_version": policy.minimum_supported_version}
