"""PlayerContentSafetyStanding — a per-player, cross-session record of accumulated
content-safety-flagged submissions and any resulting lockout (008-core-gameplay
data-model.md, FR-013)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlayerContentSafetyStanding:
    id: str
    flaggedCount: int = 0
    lockoutUntil: Optional[str] = None
    entityType: str = field(default="PlayerContentSafetyStanding")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "flaggedCount": self.flaggedCount,
            "lockoutUntil": self.lockoutUntil,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerContentSafetyStanding":
        return cls(
            id=data["id"],
            flaggedCount=data.get("flaggedCount", 0),
            lockoutUntil=data.get("lockoutUntil"),
        )
