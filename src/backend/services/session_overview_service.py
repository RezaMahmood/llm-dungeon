"""SessionOverviewService — the admin Sessions page's read model, combining every real
player session and every admin test-play session into one list (026-token-usage
data-model.md → Read model: Session Overview Row; research.md Decision 7)."""

from __future__ import annotations

from typing import Any, Optional

from backend.config import config
from backend.services.account_provisioning_service import AccountProvisioningService
from backend.services.cosmos_service import CosmosService, shared_cosmos_service
from backend.services.play_session_service import PlaySessionService
from backend.services.play_session_service import SessionNotFoundError as PlaySessionNotFoundError
from backend.services.story_service import StoryService
from backend.services.test_play_session_service import SessionNotFoundError as TestPlaySessionNotFoundError
from backend.services.test_play_session_service import TestPlaySessionService

DELETED_STORY_LABEL = "(deleted story)"
UNPROVISIONED_ACCOUNT_LABEL = "(no longer provisioned)"


class SessionNotFoundError(Exception):
    """No session with that id in either container."""


class SessionOverviewService:
    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        story_service: Optional[StoryService] = None,
        account_provisioning_service: Optional[AccountProvisioningService] = None,
        play_session_service: Optional[PlaySessionService] = None,
        test_play_session_service: Optional[TestPlaySessionService] = None,
    ) -> None:
        self._cosmos = cosmos_service or shared_cosmos_service()
        self._stories = story_service or StoryService(cosmos_service=self._cosmos)
        self._accounts = account_provisioning_service or AccountProvisioningService(cosmos_service=self._cosmos)
        self._play_sessions = play_session_service
        self._test_play_sessions = test_play_session_service

    def _play_session_service(self) -> PlaySessionService:
        if self._play_sessions is None:
            self._play_sessions = PlaySessionService(cosmos_service=self._cosmos)
        return self._play_sessions

    def _test_play_session_service(self) -> TestPlaySessionService:
        if self._test_play_sessions is None:
            self._test_play_sessions = TestPlaySessionService(cosmos_service=self._cosmos)
        return self._test_play_sessions

    def delete_session(self, session_id: str) -> str:
        """Delete the session this id names, whichever of the two containers holds it, and
        return which kind it was ("player" or "test") — 031-sessions-admin-design-spec
        FR-006.

        The id alone resolves the kind, so the client never says which container to reach
        into (research.md Decision 1). Raises `SessionNotFoundError` when neither holds
        it, which is the concurrent-delete case (FR-015)."""
        try:
            self._play_session_service().delete_session_as_administrator(session_id)
            return "player"
        except PlaySessionNotFoundError:
            pass
        try:
            self._test_play_session_service().delete_session_as_administrator(session_id)
            return "test"
        except TestPlaySessionNotFoundError as exc:
            raise SessionNotFoundError() from exc

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

        def _rows(session_type: str, container: str, entity_type: str, story_id_field: str, account_id_field: str):
            rows = self._cosmos.query(
                container,
                f"SELECT c.id, c.{story_id_field}, c.{account_id_field}, c.totalTokens "
                f"FROM c WHERE c.entityType = '{entity_type}'",
            )
            return [
                {
                    "sessionId": row["id"],
                    "sessionType": session_type,
                    "storyId": row[story_id_field],
                    "storyName": _story_name(row[story_id_field]),
                    "totalTokens": row.get("totalTokens") or 0,
                    "email": _email(row.get(account_id_field)),
                }
                for row in rows
            ]

        return _rows("player", config.PLAY_SESSIONS_CONTAINER, "PlaySession", "adventureId", "playerId") + _rows(
            "test", config.TEST_PLAY_SESSIONS_CONTAINER, "TestPlaySession", "storyId", "administratorId"
        )
