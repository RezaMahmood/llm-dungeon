"""Capability lookup service — fetches active capabilities for a user."""

from __future__ import annotations

import logging
from typing import Optional

from backend.config import config
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("capability_service")

VALID_CAPABILITIES = {"Player", "Administrator"}


class CapabilityService:
    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._request_cache: dict[str, set[str]] = {}

    def get_user_capabilities(self, user_oid: str) -> set[str]:
        """Return the set of active capabilities for a user, cached per request instance."""
        if user_oid in self._request_cache:
            return self._request_cache[user_oid]

        results = self._cosmos.query(
            config.CAPABILITY_CONTAINER,
            "SELECT * FROM c WHERE c.user_oid = @user_oid AND c.entityType = 'CapabilityAssignment' "
            "AND c.dateRevoked = null",
            params=[{"name": "@user_oid", "value": user_oid}],
            partition_key=user_oid,
        )
        capabilities = {row["capability"] for row in results if row.get("capability") in VALID_CAPABILITIES}
        logger.info("Fetched capabilities for user", extra={"user_oid": user_oid, "capabilities": sorted(capabilities)})
        self._request_cache[user_oid] = capabilities
        return capabilities

    def has_capability(self, user_oid: str, capability: str) -> bool:
        return capability in self.get_user_capabilities(user_oid)
