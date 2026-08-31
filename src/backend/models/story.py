"""Story, CharacterType, and CompletionCriteria — the persisted story configuration an
administrator builds through the 4-tab wizard and commits via explicit Save (FR-004;
data-model.md Story / Shared Structures).

Unlike the earlier auto-generated design, a Story is never required to be "complete" to
exist: only `name` is mandatory (FR-004, FR-009). Every other field is optional until an
administrator fills it in and Saves again."""

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
class Story:
    id: str
    name: str
    createdBy: str
    createdAt: str
    updatedBy: str
    updatedAt: str
    coverImageUrl: Optional[str] = None
    tone: Optional[str] = None
    readingLevel: Optional[str] = None
    sessionLengthMinutes: Optional[int] = None
    chapters: Optional[int] = None
    outline: Optional[str] = None
    rules: Optional[str] = None
    characterTypes: list[CharacterType] = field(default_factory=list)
    completionCriteria: Optional[CompletionCriteria] = None
    published: bool = False
    entityType: str = field(default="Story")

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "coverImageUrl": self.coverImageUrl,
            "tone": self.tone,
            "readingLevel": self.readingLevel,
            "sessionLengthMinutes": self.sessionLengthMinutes,
            "chapters": self.chapters,
            "outline": self.outline,
            "rules": self.rules,
            "characterTypes": [ct.to_dict() for ct in self.characterTypes],
            "completionCriteria": self.completionCriteria.to_dict() if self.completionCriteria else None,
            "published": self.published,
            "createdBy": self.createdBy,
            "createdAt": self.createdAt,
            "updatedBy": self.updatedBy,
            "updatedAt": self.updatedAt,
            "entityType": self.entityType,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        completion_criteria = data.get("completionCriteria")
        return cls(
            id=data["id"],
            name=data["name"],
            coverImageUrl=data.get("coverImageUrl"),
            tone=data.get("tone"),
            readingLevel=data.get("readingLevel"),
            sessionLengthMinutes=data.get("sessionLengthMinutes"),
            chapters=data.get("chapters"),
            outline=data.get("outline"),
            rules=data.get("rules"),
            characterTypes=[CharacterType.from_dict(ct) for ct in data.get("characterTypes", [])],
            completionCriteria=CompletionCriteria.from_dict(completion_criteria) if completion_criteria else None,
            published=data.get("published", False),
            createdBy=data["createdBy"],
            createdAt=data["createdAt"],
            updatedBy=data.get("updatedBy", data["createdBy"]),
            updatedAt=data.get("updatedAt", data["createdAt"]),
        )
