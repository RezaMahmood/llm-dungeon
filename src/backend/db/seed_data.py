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
import uuid

from azure.cosmos import PartitionKey

from backend.config import config
from backend.models.provisioned_account_entry import ProvisionedAccountEntry
from backend.models.story import CharacterType, CompletionCriteria, StartingPoint, Story
from backend.services.cosmos_service import CosmosService

TEST_USERS = [
    {"label": "Player", "roles": ["Player"]},
    {"label": "Admin", "roles": ["Administrator"]},
    {"label": "Dual-role", "roles": ["Player", "Administrator"]},
]

# 008-core-gameplay-done Phase 1 (T002): every container this backend uses locally against the
# Cosmos DB emulator, each with the partition key its Terraform resource declares
# (infrastructure/terraform/main.tf). provisionedAccountEntries is keyed by `/email`, not
# `/id`, so that an entry can be looked up before a first sign-in binds an oid — creating
# it locally with `/id` would silently break every point read against it.
CONTAINER_PARTITION_KEY_PATHS = {
    config.PROVISIONED_ACCOUNTS_CONTAINER: "/email",
    config.STORY_DRAFTS_CONTAINER: "/id",
    config.STORIES_CONTAINER: "/id",
    config.PLAY_SESSIONS_CONTAINER: "/id",
    config.PLAYER_CONTENT_SAFETY_STANDINGS_CONTAINER: "/id",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_containers(cosmos: CosmosService | None = None) -> None:
    """Create-if-not-exists every container this backend reads/writes locally, each with
    the partition key its Terraform resource declares."""
    service = cosmos or CosmosService()
    for name, partition_key_path in CONTAINER_PARTITION_KEY_PATHS.items():
        service.database.create_container_if_not_exists(
            id=name, partition_key=PartitionKey(path=partition_key_path)
        )


def seed_stories(cosmos: CosmosService | None = None) -> list[str]:
    """Two additional published stories for 008-core-gameplay-done's quickstart scenarios: one
    with a short `maxDurationMinutes` (Scenario 3), one with an easily-triggered
    `successConditions` entry plus a second condition usable for `rule: "any"`/`"all"`
    variants (Scenario 4)."""
    service = cosmos or CosmosService()
    container = service.get_container(config.STORIES_CONTAINER)
    created_at = _now()

    duration_story = Story(
        id=str(uuid.uuid4()),
        name="The Minute at Mudlark Hall",
        worldPrompt="A crumbling manor with one working clock, ticking down to nothing in particular.",
        characterTypes=[CharacterType(name="Caretaker")],
        completionCriteria=CompletionCriteria(successConditions=["Find the ninth door"], maxDurationMinutes=1),
        narrativeGuidance="Keep it eerie but never actually dangerous.",
        startingPoint=StartingPoint(
            narrativeText="The hall's one working clock ticks somewhere above you, and every other room is silent.",
            suggestedActions=["Follow the ticking upstairs", "Try the nearest door"],
            locationLabel="Mudlark Hall entrance",
            goalLabel="Find the ninth door",
        ),
        createdBy="seed_data.py",
        createdAt=created_at,
        contentUpdatedAt=created_at,
        published=True,
    )
    container.upsert_item(duration_story.to_dict())

    success_story = Story(
        id=str(uuid.uuid4()),
        name="The Lighthouse at Gullwing Cove",
        worldPrompt="A half-abandoned lighthouse on a foggy cove, its keeper long gone.",
        characterTypes=[CharacterType(name="Curious Cousin")],
        completionCriteria=CompletionCriteria(
            successConditions=["the player says the word lighthouse", "the player lights the lamp"],
            failureConditions=["the player leaves the cove"],
            rule="any",
        ),
        narrativeGuidance="Keep it eerie but never actually dangerous.",
        startingPoint=StartingPoint(
            narrativeText="Fog rolls off the cove, and the lighthouse stands dark at the end of the path.",
            suggestedActions=["Walk up to the lighthouse", "Search the shoreline"],
            locationLabel="Gullwing Cove path",
            goalLabel="Light the lamp",
        ),
        createdBy="seed_data.py",
        createdAt=created_at,
        contentUpdatedAt=created_at,
        published=True,
    )
    container.upsert_item(success_story.to_dict())

    print(f"Seeded story: {duration_story.name} ({duration_story.id})")
    print(f"Seeded story: {success_story.name} ({success_story.id})")
    return [duration_story.id, success_story.id]


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
    ensure_containers()
    seed()
    seed_stories()
