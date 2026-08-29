"""Populate test allow-list and capability data in Cosmos DB.

Run manually against a real Cosmos DB account once 007's infrastructure and
this feature's collections exist:

    python -m backend.db.seed_data

Requires COSMOS_ENDPOINT to be set and the caller's identity (or the Function
App's Managed Identity, if run from within Azure) to hold the
`Cosmos DB Data Contributor` role on the account.
"""

from __future__ import annotations

import datetime
import uuid

from backend.config import config
from backend.models.allow_list_entry import AllowListEntry
from backend.models.capability_assignment import CapabilityAssignment
from backend.services.cosmos_service import CosmosService

TEST_USERS = [
    {"label": "Player", "capabilities": ["Player"]},
    {"label": "Admin", "capabilities": ["Administrator"]},
    {"label": "Dual-role", "capabilities": ["Player", "Administrator"]},
]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seed(cosmos: CosmosService | None = None) -> list[str]:
    """Insert three test users (Player, Admin, Dual-role) with allow-list entries
    and capability assignments. Returns the generated user_oids."""
    service = cosmos or CosmosService()
    allow_list_container = service.get_container(config.ALLOW_LIST_CONTAINER)
    capability_container = service.get_container(config.CAPABILITY_CONTAINER)

    created_oids = []
    for user in TEST_USERS:
        user_oid = str(uuid.uuid4())
        created_oids.append(user_oid)

        entry = AllowListEntry(
            user_oid=user_oid,
            email=f"{user['label'].lower().replace('-', '')}@example.com",
            dateAdded=_now(),
            addedBy="seed_data.py",
            notes=f"Seeded test account: {user['label']}",
        )
        allow_list_container.upsert_item(entry.to_dict())

        for capability in user["capabilities"]:
            assignment = CapabilityAssignment(
                user_oid=user_oid,
                capability=capability,
                dateAssigned=_now(),
                assignedBy="seed_data.py",
            )
            capability_container.upsert_item(assignment.to_dict())

        print(f"Seeded {user['label']} user: {user_oid} ({', '.join(user['capabilities'])})")

    return created_oids


if __name__ == "__main__":
    seed()
