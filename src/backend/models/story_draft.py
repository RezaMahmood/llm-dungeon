"""StoryDraft — the in-progress wizard session that generates into a Story
(models/story.py) once the Completeness Rule is met (data-model.md Story Draft,
research.md §3). No conversation history is kept: the world-prompt suggestion is a single
pass whose result lands in `worldPrompt` and nowhere else (#227)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models.story import CharacterType, CompletionCriteria

# Cosmos TTL (seconds) reset on every draft write — an abandoned draft is auto-expired
# with no application cleanup code (research.md §3, FR-005).
DRAFT_TTL_SECONDS = 24 * 60 * 60


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    # Mirrors Story.blurb (028-home-page-redesign FR-016) — not part of the Completeness
    # Rule below; a blurb is not required for generation.
    blurb: Optional[str] = None
    characterTypes: list[CharacterType] = field(default_factory=list)
    completionCriteria: Optional[CompletionCriteria] = None
    createdAt: str = field(default_factory=_now)
    updatedAt: str = field(default_factory=_now)
    ttl: int = DRAFT_TTL_SECONDS
    entityType: str = field(default="StoryDraft")
    # None => creation draft (generates a new Story). Set => edit draft, bound to that
    # Story and pinned to the contentVersion it was seeded from (data-model.md → StoryDraft).
    sourceStoryId: Optional[str] = None
    baseContentVersion: Optional[int] = None
    # Tokens spent by suggest_world_prompt calls made against this draft (data-model.md →
    # StoryDraft); folded into the Story's totalTokens when this draft converts.
    totalTokens: int = 0

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
            "blurb": self.blurb,
            "characterTypes": [ct.to_dict() for ct in self.characterTypes],
            "completionCriteria": self.completionCriteria.to_dict() if self.completionCriteria else None,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "ttl": self.ttl,
            "entityType": self.entityType,
            "sourceStoryId": self.sourceStoryId,
            "baseContentVersion": self.baseContentVersion,
            "totalTokens": self.totalTokens,
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
            blurb=data.get("blurb"),
            characterTypes=[CharacterType.from_dict(ct) for ct in data.get("characterTypes", [])],
            completionCriteria=CompletionCriteria.from_dict(completion_criteria) if completion_criteria else None,
            createdAt=data.get("createdAt", _now()),
            updatedAt=data.get("updatedAt", _now()),
            ttl=data.get("ttl", DRAFT_TTL_SECONDS),
            sourceStoryId=data.get("sourceStoryId"),
            baseContentVersion=data.get("baseContentVersion"),
            totalTokens=data.get("totalTokens", 0),
        )
