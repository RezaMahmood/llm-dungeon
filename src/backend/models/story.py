"""Story, CharacterType, and CompletionCriteria — the persisted, published-by-default story
configuration a StoryDraft (models/story_draft.py) generates into (data-model.md Story /
Shared Structures)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

VALID_RULES = {"any", "all"}


@dataclass
class CharacterType:
    name: str
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterType":
        return cls(name=data["name"], description=data.get("description"))


@dataclass
class CompletionCriteria:
    successConditions: list[str]
    maxDurationMinutes: Optional[int] = None
    failureConditions: list[str] = field(default_factory=list)
    rule: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.successConditions:
            raise ValueError("successConditions must have at least one entry")

        total_conditions = len(self.successConditions) + len(self.failureConditions)
        if total_conditions > 1:
            if not self.rule:
                raise ValueError("rule is required when more than one condition is defined")
            if self.rule not in VALID_RULES:
                raise ValueError(f"rule must be one of {sorted(VALID_RULES)}, got {self.rule!r}")
        else:
            self.rule = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "maxDurationMinutes": self.maxDurationMinutes,
            "successConditions": self.successConditions,
            "failureConditions": self.failureConditions,
            "rule": self.rule,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompletionCriteria":
        return cls(
            successConditions=list(data.get("successConditions", [])),
            maxDurationMinutes=data.get("maxDurationMinutes"),
            failureConditions=list(data.get("failureConditions", [])),
            rule=data.get("rule"),
        )


@dataclass
class StartingPoint:
    """The story's fixed opening — generated once at story-creation time and replayed
    verbatim as every session's turn 0 (008-core-gameplay-done data-model.md → Player
    Interaction). Its fields are exactly the ones a turn carries, minus the per-session
    ones (`turnNumber`, `playerInput`, `timestamp`)."""

    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None

    def __post_init__(self) -> None:
        if not self.narrativeText:
            raise ValueError("narrativeText is required")
        if not self.suggestedActions:
            raise ValueError("suggestedActions must have at least one entry")
        if not self.locationLabel:
            raise ValueError("locationLabel is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "narrativeText": self.narrativeText,
            "suggestedActions": self.suggestedActions,
            "locationLabel": self.locationLabel,
            "goalLabel": self.goalLabel,
            "progress": self.progress,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StartingPoint":
        return cls(
            narrativeText=data["narrativeText"],
            suggestedActions=list(data.get("suggestedActions", [])),
            locationLabel=data["locationLabel"],
            goalLabel=data.get("goalLabel"),
            progress=data.get("progress"),
        )


@dataclass
class Story:
    id: str
    worldPrompt: str
    characterTypes: list[CharacterType]
    completionCriteria: CompletionCriteria
    narrativeGuidance: str
    createdBy: str
    createdAt: str
    contentUpdatedAt: str
    name: Optional[str] = None
    coverImageUrl: Optional[str] = None
    tone: Optional[str] = None
    readingLevel: Optional[str] = None
    sessionLengthMinutes: Optional[int] = None
    chapters: Optional[int] = None
    rules: Optional[str] = None
    published: bool = False
    lastPublishedAt: Optional[str] = None
    lastTestPlayedAt: Optional[str] = None
    lastUpdatedBy: Optional[str] = None
    contentVersion: int = 1
    # Optional only for Story rows persisted before this field existed; those are
    # backfilled on their next session start (StoryService.ensure_starting_point).
    startingPoint: Optional[StartingPoint] = None
    entityType: str = field(default="Story")

    def __post_init__(self) -> None:
        if not self.worldPrompt:
            raise ValueError("worldPrompt is required")
        if not self.characterTypes:
            raise ValueError("characterTypes must have at least one entry")
        if not self.narrativeGuidance:
            raise ValueError("narrativeGuidance is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "coverImageUrl": self.coverImageUrl,
            "tone": self.tone,
            "readingLevel": self.readingLevel,
            "sessionLengthMinutes": self.sessionLengthMinutes,
            "chapters": self.chapters,
            "worldPrompt": self.worldPrompt,
            "rules": self.rules,
            "characterTypes": [ct.to_dict() for ct in self.characterTypes],
            "completionCriteria": self.completionCriteria.to_dict(),
            "narrativeGuidance": self.narrativeGuidance,
            "startingPoint": self.startingPoint.to_dict() if self.startingPoint else None,
            "published": self.published,
            "lastPublishedAt": self.lastPublishedAt,
            "createdBy": self.createdBy,
            "createdAt": self.createdAt,
            "contentUpdatedAt": self.contentUpdatedAt,
            "lastTestPlayedAt": self.lastTestPlayedAt,
            "lastUpdatedBy": self.lastUpdatedBy,
            "contentVersion": self.contentVersion,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        return cls(
            id=data["id"],
            name=data.get("name"),
            coverImageUrl=data.get("coverImageUrl"),
            tone=data.get("tone"),
            readingLevel=data.get("readingLevel"),
            sessionLengthMinutes=data.get("sessionLengthMinutes"),
            chapters=data.get("chapters"),
            worldPrompt=data["worldPrompt"],
            rules=data.get("rules"),
            characterTypes=[CharacterType.from_dict(ct) for ct in data.get("characterTypes", [])],
            completionCriteria=CompletionCriteria.from_dict(data["completionCriteria"]),
            narrativeGuidance=data["narrativeGuidance"],
            startingPoint=(
                StartingPoint.from_dict(data["startingPoint"]) if data.get("startingPoint") else None
            ),
            published=data.get("published", False),
            lastPublishedAt=data.get("lastPublishedAt"),
            createdBy=data["createdBy"],
            createdAt=data["createdAt"],
            # Falls back to createdAt for Story rows persisted before this field existed —
            # without this, every pre-existing story would raise KeyError on the next read.
            contentUpdatedAt=data.get("contentUpdatedAt", data["createdAt"]),
            lastTestPlayedAt=data.get("lastTestPlayedAt"),
            # Both fall back for Story rows persisted before this feature existed
            # (data-model.md → Story), matching the contentUpdatedAt precedent above.
            lastUpdatedBy=data.get("lastUpdatedBy"),
            contentVersion=data.get("contentVersion", 1),
        )
