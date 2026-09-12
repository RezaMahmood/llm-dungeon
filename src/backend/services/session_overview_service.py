"""SessionOverviewService — the admin Sessions page's read model, combining every real
player session and every admin test-play session into one list (026-token-usage
data-model.md → Read model: Session Overview Row; research.md Decision 7)."""

from __future__ import annotations

from typing import Any, Optional

from backend.config import config
from backend.services.account_provisioning_service import AccountProvisioningService
from backend.services.cosmos_service import CosmosService, shared_cosmos_service
from backend.services.story_service import StoryService

DELETED_STORY_LABEL = "(deleted story)"
UNPROVISIONED_ACCOUNT_LABEL = "(no longer provisioned)"


class SessionOverviewService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        story_service: Optional[StoryService] = None,
        account_provisioning_service: Optional[AccountProvisioningService] = None,
    ) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()
        self._stories = story_service or StoryService(cosmos_service=self._cosmos)
        self._accounts = account_provisioning_service or AccountProvisioningService(cosmos_service=self._cosmos)

    def list_sessions(self) -> list[dict[str, Any]]:
        """Every `PlaySession` and every `TestPlaySession`, regardless of `status`
        (data-model.md Validation Rules) — no pagination/filtering/sorting in v1
        (spec.md Assumptions)."""
        email_by_object_id = {
            entry.objectId: entry.email for entry in self._accounts.list_all() if entry.objectId
        }
        story_names: dict[str, str] = {}

        def _story_name(story_id: str) -> str:
            if story_id not in story_names:
                name = self._stories.get_story_name(story_id)
                story_names[story_id] = name if name is not None else DELETED_STORY_LABEL
            return story_names[story_id]

        def _email(object_id: Optional[str]) -> str:
            return email_by_object_id.get(object_id, UNPROVISIONED_ACCOUNT_LABEL)

        player_rows = self._cosmos.query(
            config.PLAY_SESSIONS_CONTAINER,
            "SELECT c.id, c.adventureId, c.playerId, c.totalTokens FROM c WHERE c.entityType = 'PlaySession'",
        )
        test_rows = self._cosmos.query(
            config.TEST_PLAY_SESSIONS_CONTAINER,
            "SELECT c.id, c.storyId, c.administratorId, c.totalTokens FROM c WHERE c.entityType = 'TestPlaySession'",
        )

        sessions = [
            {
                "sessionId": row["id"],
                "sessionType": "player",
                "storyId": row["adventureId"],
                "storyName": _story_name(row["adventureId"]),
                "totalTokens": row.get("totalTokens") or 0,
                "email": _email(row.get("playerId")),
            }
            for row in player_rows
        ]
        sessions.extend(
            {
                "sessionId": row["id"],
                "sessionType": "test",
                "storyId": row["storyId"],
                "storyName": _story_name(row["storyId"]),
                "totalTokens": row.get("totalTokens") or 0,
                "email": _email(row.get("administratorId")),
            }
            for row in test_rows
        )
        return sessions
