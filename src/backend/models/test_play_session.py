"""TestPlaySession and TestPlayExchange — an administrator's interactive test playthrough
of a draft story, persisted separately from `playSessions` so no player route can ever
reach it (010-story-test-play-done data-model.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TestPlayExchange:
    turnNumber: int
    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    timestamp: str
    playerInput: Optional[str] = None
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None
    # This exchange's own token count; 0 for a content-filtered deflection turn
    # (data-model.md → TestPlaySession).
    tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "turnNumber": self.turnNumber,
            "playerInput": self.playerInput,
            "narrativeText": self.narrativeText,
            "suggestedActions": self.suggestedActions,
            "locationLabel": self.locationLabel,
            "goalLabel": self.goalLabel,
            "progress": self.progress,
            "timestamp": self.timestamp,
            "tokens": self.tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestPlayExchange":
        return cls(
            turnNumber=data["turnNumber"],
            playerInput=data.get("playerInput"),
            narrativeText=data["narrativeText"],
            suggestedActions=list(data.get("suggestedActions", [])),
            locationLabel=data["locationLabel"],
            goalLabel=data.get("goalLabel"),
            progress=data.get("progress"),
            timestamp=data["timestamp"],
            tokens=data.get("tokens", 0),
        )


@dataclass
class TestPlaySession:
    id: str
    storyId: str
    administratorId: str
    characterName: str
    characterType: str
    startedAt: str
    lastInteractionAt: str
    status: str = "active"
    completionReason: Optional[dict[str, Any]] = None
    satisfiedSuccessConditions: list[int] = field(default_factory=list)
    satisfiedFailureConditions: list[int] = field(default_factory=list)
    interactionInProgress: bool = False
    turns: list[TestPlayExchange] = field(default_factory=list)
    endedAt: Optional[str] = None
    summary: Optional[str] = None
    summarizedThroughTurn: int = 0
    entityType: str = field(default="TestPlaySession")
    # Running cumulative token total for this test-play session (data-model.md →
    # TestPlaySession) — also added to Story.totalTokens (research.md Decision 3).
    totalTokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "storyId": self.storyId,
            "administratorId": self.administratorId,
            "characterName": self.characterName,
            "characterType": self.characterType,
            "status": self.status,
            "completionReason": self.completionReason,
            "satisfiedSuccessConditions": self.satisfiedSuccessConditions,
            "satisfiedFailureConditions": self.satisfiedFailureConditions,
            "interactionInProgress": self.interactionInProgress,
            "turns": [turn.to_dict() for turn in self.turns],
            "startedAt": self.startedAt,
            "lastInteractionAt": self.lastInteractionAt,
            "endedAt": self.endedAt,
            "summary": self.summary,
            "summarizedThroughTurn": self.summarizedThroughTurn,
            "totalTokens": self.totalTokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestPlaySession":
        return cls(
            id=data["id"],
            storyId=data["storyId"],
            administratorId=data["administratorId"],
            characterName=data["characterName"],
            characterType=data["characterType"],
            status=data.get("status", "active"),
            completionReason=data.get("completionReason"),
            satisfiedSuccessConditions=list(data.get("satisfiedSuccessConditions", [])),
            satisfiedFailureConditions=list(data.get("satisfiedFailureConditions", [])),
            interactionInProgress=data.get("interactionInProgress", False),
            turns=[TestPlayExchange.from_dict(turn) for turn in data.get("turns", [])],
            startedAt=data["startedAt"],
            lastInteractionAt=data["lastInteractionAt"],
            endedAt=data.get("endedAt"),
            summary=data.get("summary"),
            summarizedThroughTurn=data.get("summarizedThroughTurn", 0),
            totalTokens=data.get("totalTokens", 0),
        )
