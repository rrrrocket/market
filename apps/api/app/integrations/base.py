from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class ProviderMetadata:
    code: str
    name: str
    category: str
    capabilities: tuple[str, ...]
    reliability: str
    enabled: bool
    health: str = "NOT_CONNECTED"
    last_sync: datetime | None = None
    rate_limit: str | None = None

    def model_dump(self) -> dict:
        value = asdict(self)
        value["last_sync"] = self.last_sync.isoformat() if self.last_sync else None
        return value


class Provider(Protocol):
    metadata: ProviderMetadata


def unavailable_metadata(
    code: str,
    name: str,
    category: str,
    capabilities: tuple[str, ...],
    reliability: str,
) -> ProviderMetadata:
    return ProviderMetadata(
        code=code,
        name=name,
        category=category,
        capabilities=capabilities,
        reliability=reliability,
        enabled=False,
        health="NOT_CONNECTED",
    )


def observed_now() -> datetime:
    return datetime.now(UTC)
