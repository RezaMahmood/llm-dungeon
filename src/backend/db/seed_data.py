"""Populate test provisioned-account data in Cosmos DB.

Run manually against a real Cosmos DB account once 007's infrastructure and
this feature's collections exist:

    python -m backend.db.seed_data

Requires COSMOS_ENDPOINT to be set and the caller's identity (or the Function
App's Managed Identity, if run from within Azure) to hold the
`Cosmos DB Data Contributor` role on the account.
"""

from __future__ import annotations

import datetime

from backend.config import config
from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.services.cosmos_service import CosmosService

TEST_USERS = [
    {"label": "Player", "roles": ["Player"]},
    {"label": "Admin", "roles": ["Administrator"]},
    {"label": "Dual-role", "roles": ["Player", "Administrator"]},
]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def seed(cosmos: CosmosService | None = None) -> list[str]:
    """Insert three test provisioned account entries (Player, Admin, Dual-role),
    unbound (objectId=None) until each account's first sign-in. Returns the
    generated emails."""
    service = cosmos or CosmosService()
    container = service.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)

    created_emails = []
    for user in TEST_USERS:
        email = f"{user['label'].lower().replace('-', '')}@example.com"
        created_emails.append(email)

        entry = ProvisionedAccountEntry(
            email=email,
            roles=user["roles"],
            dateAdded=_now(),
            addedBy="seed_data.py",
        )
        container.upsert_item(entry.to_dict())

        print(f"Seeded {user['label']} user: {email} ({', '.join(user['roles'])})")

    return created_emails


if __name__ == "__main__":
    seed()
