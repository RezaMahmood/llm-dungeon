"""Allow-list service — determines whether a user may sign in."""

from __future__ import annotations

import logging
from typing import Optional

from backend.config import config
from backend.models.allow_list_entry import AllowListEntry
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("allow_list_service")


class AllowListService:
    """Checks allow-list membership. Never reveals whether an oid exists to callers
    beyond a plain boolean — no account enumeration."""

    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or CosmosService()

    def get_allow_list_entry(self, user_oid: str) -> Optional[AllowListEntry]:
        results = self._cosmos.query(
            config.ALLOW_LIST_CONTAINER,
            "SELECT * FROM c WHERE c.user_oid = @user_oid AND c.entityType = 'AllowListEntry' "
            "AND c.dateRemoved = null",
            params=[{"name": "@user_oid", "value": user_oid}],
            partition_key=user_oid,
        )
        if not results:
            return None
        return AllowListEntry.from_dict(results[0])

    def is_allowed(self, user_oid: str) -> bool:
        entry = self.get_allow_list_entry(user_oid)
        allowed = entry is not None and entry.is_active()
        logger.info("Allow-list check", extra={"user_oid": user_oid, "allowed": allowed})
        return allowed
