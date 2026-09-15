"""AvatarSetupAttempts — a per-(player, story) counter bounding model-backed avatar-
description validation attempts within a single setup (032-story-archetypes-player-avatar
research.md Decision 3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AvatarSetupAttempts:
    id: str
    playerId: str
    storyId: str
    modelBackedAttempts: int = 0
    entityType: str = field(default="AvatarSetupAttempts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "playerId": self.playerId,
            "storyId": self.storyId,
            "modelBackedAttempts": self.modelBackedAttempts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AvatarSetupAttempts":
        return cls(
            id=data["id"],
            playerId=data["playerId"],
            storyId=data["storyId"],
            modelBackedAttempts=data.get("modelBackedAttempts", 0),
        )
