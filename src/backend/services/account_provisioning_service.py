"""Account provisioning service — email-first-match, oid-bind-thereafter sign-in resolution."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from pyisemail import is_email

from backend.config import config
from backend.models.provisioned_account_entry import VALID_ROLES, ProvisionedAccountEntry
from backend.services.cosmos_service import CosmosService

logger = logging.getLogger("account_provisioning_service")


class InvalidEmailError(ValueError):
    """Raised when an email fails RFC 5322 validation (FR-005)."""


class RoleRequiredError(ValueError):
    """Raised when no valid role is supplied (FR-003/FR-004)."""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AccountProvisioningService:
    """Looks up, binds, adds, merges, and lists Provisioned Account Entries."""

    def __init__(self, cosmos_service: Optional[CosmosService] = None) -> None:
        self._cosmos = cosmos_service or CosmosService()

    def get_by_email(self, email: str) -> Optional[ProvisionedAccountEntry]:
        """Point read by lowercased email."""
        email = email.lower()
        container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
        try:
            item = container.read_item(item=email, partition_key=email)
        except Exception:  # noqa: BLE001 - Cosmos raises CosmosResourceNotFoundError on a miss
            return None
        return ProvisionedAccountEntry.from_dict(item)

    def authorize_sign_in(self, email: str, oid: str) -> tuple[bool, Optional[ProvisionedAccountEntry]]:
        """Resolve a sign-in by email, then bind or verify the token's oid (FR-006/FR-007).

        Returns (is_authorized, entry). No entry -> (False, None). Unbound entry -> bind
        oid, persist, and allow. Matching bound oid -> allow. Mismatched bound oid -> deny.
        """
        entry = self.get_by_email(email)
        if entry is None:
            return False, None

        if entry.objectId is None:
            entry.objectId = oid
            entry.dateBound = _now()
            container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
            container.upsert_item(entry.to_dict())
            return True, entry

        if entry.objectId == oid:
            return True, entry

        logger.info("Sign-in denied: bound objectId does not match token oid", extra={"email": email})
        return False, None

    def ensure_seed_administrator(self, email: str) -> None:
        """Create the seed Administrator entry if absent (FR-001). Never overwrites an
        existing entry's roles."""
        if not email:
            return
        if self.get_by_email(email) is not None:
            return

        entry = ProvisionedAccountEntry(
            email=email,
            roles=["Administrator"],
            dateAdded=_now(),
            addedBy="seed",
        )
        container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
        container.upsert_item(entry.to_dict())
        logger.info("Seed administrator created", extra={"email": entry.email})

    def add_or_merge(self, email: str, roles: list[str], added_by: Optional[str] = None) -> ProvisionedAccountEntry:
        """Create a new entry, or merge roles into an existing one (FR-002/003/004/005/009).

        Validates email via pyisemail and roles as a non-empty subset of VALID_ROLES,
        raising InvalidEmailError/RoleRequiredError the caller maps to invalid_email/
        role_required. On an existing email, unions roles and leaves objectId/dateBound
        untouched; resubmitting identical roles is a no-op write.
        """
        if not email or not is_email(email):
            raise InvalidEmailError(f"{email!r} is not a valid email address")

        role_set = set(roles or [])
        if not role_set or not role_set.issubset(VALID_ROLES):
            raise RoleRequiredError("At least one valid role (Player and/or Administrator) is required")

        normalized_email = email.lower()
        existing = self.get_by_email(normalized_email)

        if existing is None:
            entry = ProvisionedAccountEntry(
                email=normalized_email,
                roles=sorted(role_set),
                dateAdded=_now(),
                addedBy=added_by,
            )
        else:
            merged_roles = sorted(set(existing.roles) | role_set)
            entry = existing
            entry.roles = merged_roles

        container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
        container.upsert_item(entry.to_dict())
        return entry

    def list_all(self) -> list[ProvisionedAccountEntry]:
        """Return every Provisioned Account Entry (FR-010)."""
        results = self._cosmos.query(
            config.PROVISIONED_ACCOUNTS_CONTAINER,
            "SELECT * FROM c WHERE c.entityType = 'ProvisionedAccountEntry'",
        )
        return [ProvisionedAccountEntry.from_dict(row) for row in results]
