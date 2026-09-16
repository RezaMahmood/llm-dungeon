"""AvatarSetupAttempts — a per-(player, story) counter bounding model-backed avatar-
description validation attempts within a single setup (032-story-archetypes-player-avatar
research.md Decision 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AvatarSetupAttempts:
    id: str
    playerId: str
    storyId: str
    modelBackedAttempts: int = 0
    # When the current counting window opened. The cap is a rolling window, not a
    # permanent ceiling: without this the counter only ever cleared on a successful
    # session creation, which a capped player could never reach, so reaching the cap
    # locked them out of that adventure for good. `None` on a document written before
    # this field existed, which reads as an expired window (issue #361 convergence).
    windowStartedAt: Optional[str] = None
    entityType: str = field(default="AvatarSetupAttempts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "playerId": self.playerId,
            "storyId": self.storyId,
            "modelBackedAttempts": self.modelBackedAttempts,
            "windowStartedAt": self.windowStartedAt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AvatarSetupAttempts":
        return cls(
            id=data["id"],
            playerId=data["playerId"],
            storyId=data["storyId"],
            modelBackedAttempts=data.get("modelBackedAttempts", 0),
            windowStartedAt=data.get("windowStartedAt"),
        )
