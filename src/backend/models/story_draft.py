"""StoryDraft and StoryCreationExchange — the in-progress wizard/conversation session that
generates into a Story (models/story.py) once the Completeness Rule is met (data-model.md
Story Draft, research.md §3)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models.story import CharacterType, CompletionCriteria

VALID_ROLES = {"administrator", "system"}

# Cosmos TTL (seconds) reset on every draft write — an abandoned draft is auto-expired
# with no application cleanup code (research.md §3, FR-005).
DRAFT_TTL_SECONDS = 24 * 60 * 60


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class StoryCreationExchange:
    role: str
    message: str
    timestamp: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.role not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}, got {self.role!r}")
        if not self.message:
            raise ValueError("message is required")

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "message": self.message, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryCreationExchange":
        return cls(role=data["role"], message=data["message"], timestamp=data["timestamp"])


@dataclass
class StoryDraft:
    id: str
    createdBy: str
    name: Optional[str] = None
    coverImageUrl: Optional[str] = None
    tone: Optional[str] = None
    readingLevel: Optional[str] = None
    sessionLengthMinutes: Optional[int] = None
    chapters: Optional[int] = None
    worldPrompt: Optional[str] = None
    rules: Optional[str] = None
    characterTypes: list[CharacterType] = field(default_factory=list)
    completionCriteria: Optional[CompletionCriteria] = None
    exchanges: list[StoryCreationExchange] = field(default_factory=list)
    createdAt: str = field(default_factory=_now)
    updatedAt: str = field(default_factory=_now)
    ttl: int = DRAFT_TTL_SECONDS
    entityType: str = field(default="StoryDraft")

    def is_complete(self) -> bool:
        """The Completeness Rule (data-model.md) — generation triggers on the write that
        makes this true (FR-003/FR-004)."""
        return bool(
            self.name
            and self.worldPrompt
            and self.characterTypes
            and self.completionCriteria
            and self.completionCriteria.successConditions
        )

    def touch(self) -> None:
        """Refresh updatedAt and reset the TTL clock — called on every write (research.md §3)."""
        self.updatedAt = _now()
        self.ttl = DRAFT_TTL_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "createdBy": self.createdBy,
            "name": self.name,
            "coverImageUrl": self.coverImageUrl,
            "tone": self.tone,
            "readingLevel": self.readingLevel,
            "sessionLengthMinutes": self.sessionLengthMinutes,
            "chapters": self.chapters,
            "worldPrompt": self.worldPrompt,
            "rules": self.rules,
            "characterTypes": [ct.to_dict() for ct in self.characterTypes],
            "completionCriteria": self.completionCriteria.to_dict() if self.completionCriteria else None,
            "exchanges": [ex.to_dict() for ex in self.exchanges],
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "ttl": self.ttl,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoryDraft":
        completion_criteria = data.get("completionCriteria")
        return cls(
            id=data["id"],
            createdBy=data["createdBy"],
            name=data.get("name"),
            coverImageUrl=data.get("coverImageUrl"),
            tone=data.get("tone"),
            readingLevel=data.get("readingLevel"),
            sessionLengthMinutes=data.get("sessionLengthMinutes"),
            chapters=data.get("chapters"),
            worldPrompt=data.get("worldPrompt"),
            rules=data.get("rules"),
            characterTypes=[CharacterType.from_dict(ct) for ct in data.get("characterTypes", [])],
            completionCriteria=CompletionCriteria.from_dict(completion_criteria) if completion_criteria else None,
            exchanges=[StoryCreationExchange.from_dict(ex) for ex in data.get("exchanges", [])],
            createdAt=data.get("createdAt", _now()),
            updatedAt=data.get("updatedAt", _now()),
            ttl=data.get("ttl", DRAFT_TTL_SECONDS),
        )
