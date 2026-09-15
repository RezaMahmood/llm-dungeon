"""StoredAvatarDescription — a per-(player, story) record of the most recent avatar
description that player used for that adventure (034-avatar-memory-and-visibility
data-model.md), offered back as a setup prefill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoredAvatarDescription:
    id: str
    playerId: str
    storyId: str
    description: str
    updatedAt: str
    entityType: str = field(default="StoredAvatarDescription")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "playerId": self.playerId,
            "storyId": self.storyId,
            "description": self.description,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredAvatarDescription":
        return cls(
            id=data["id"],
            playerId=data["playerId"],
            storyId=data["storyId"],
            description=data["description"],
            updatedAt=data["updatedAt"],
        )
