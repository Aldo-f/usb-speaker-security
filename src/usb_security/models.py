from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Device:
    identifier: str
    name: str
    removable: bool
    whole_disk: bool
    read_only: bool | None
    transport: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationResult:
    action: str
    device: str
    verified: bool
    scope: str
    rollback: str
    details: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
