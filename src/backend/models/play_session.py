"""PlaySession and PlayerInteraction — one player's individual playthrough of a published
Story, persisted so it survives across the independent HTTP requests that make up a play
session (008-core-gameplay-done data-model.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlayerInteraction:
    turnNumber: int
    narrativeText: str
    suggestedActions: list[str]
    locationLabel: str
    timestamp: str
    playerInput: Optional[str] = None
    goalLabel: Optional[str] = None
    progress: Optional[dict[str, int]] = None
    # This turn's own token count; 0 for turn 0 (replayed verbatim, no LLM call) and for a
    # content-filtered deflection turn (data-model.md → PlaySession).
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
    def from_dict(cls, data: dict[str, Any]) -> "PlayerInteraction":
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
class CheckpointMarker:
    """A labelled, timestamped save point recorded by the player (009-save-and-continue).
    History only — it carries no game state and can never be resumed from."""

    label: str
    turnNumber: int
    createdAt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "turnNumber": self.turnNumber,
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointMarker":
        return cls(
            label=data["label"],
            turnNumber=data["turnNumber"],
            createdAt=data["createdAt"],
        )


@dataclass
class PlaySession:
    id: str
    adventureId: str
    playerId: str
    characterName: str
    characterType: str
    startedAt: str
    lastInteractionAt: str
    status: str = "active"
    completionReason: Optional[dict[str, Any]] = None
    satisfiedSuccessConditions: list[int] = field(default_factory=list)
    satisfiedFailureConditions: list[int] = field(default_factory=list)
    interactionInProgress: bool = False
    isActiveForPlayer: bool = True
    turns: list[PlayerInteraction] = field(default_factory=list)
    endedAt: Optional[str] = None
    summary: Optional[str] = None
    summarizedThroughTurn: int = 0
    checkpoints: list[CheckpointMarker] = field(default_factory=list)
    entityType: str = field(default="PlaySession")
    # Running cumulative token total across every turn and summarization call in this
    # session; never contributes to Story.totalTokens (data-model.md → PlaySession).
    totalTokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entityType": self.entityType,
            "adventureId": self.adventureId,
            "playerId": self.playerId,
            "characterName": self.characterName,
            "characterType": self.characterType,
            "status": self.status,
            "completionReason": self.completionReason,
            "satisfiedSuccessConditions": self.satisfiedSuccessConditions,
            "satisfiedFailureConditions": self.satisfiedFailureConditions,
            "interactionInProgress": self.interactionInProgress,
            "isActiveForPlayer": self.isActiveForPlayer,
            "turns": [turn.to_dict() for turn in self.turns],
            "startedAt": self.startedAt,
            "lastInteractionAt": self.lastInteractionAt,
            "endedAt": self.endedAt,
            "summary": self.summary,
            "summarizedThroughTurn": self.summarizedThroughTurn,
            "checkpoints": [checkpoint.to_dict() for checkpoint in self.checkpoints],
            "totalTokens": self.totalTokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlaySession":
        return cls(
            id=data["id"],
            adventureId=data["adventureId"],
            playerId=data["playerId"],
            characterName=data["characterName"],
            characterType=data["characterType"],
            status=data.get("status", "active"),
            completionReason=data.get("completionReason"),
            satisfiedSuccessConditions=list(data.get("satisfiedSuccessConditions", [])),
            satisfiedFailureConditions=list(data.get("satisfiedFailureConditions", [])),
            interactionInProgress=data.get("interactionInProgress", False),
            isActiveForPlayer=data.get("isActiveForPlayer", True),
            turns=[PlayerInteraction.from_dict(turn) for turn in data.get("turns", [])],
            startedAt=data["startedAt"],
            lastInteractionAt=data["lastInteractionAt"],
            endedAt=data.get("endedAt"),
            summary=data.get("summary"),
            summarizedThroughTurn=data.get("summarizedThroughTurn", 0),
            checkpoints=[CheckpointMarker.from_dict(checkpoint) for checkpoint in data.get("checkpoints", [])],
            totalTokens=data.get("totalTokens", 0),
        )
