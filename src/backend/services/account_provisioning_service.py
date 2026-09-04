"""Account provisioning service — email-first-match, oid-bind-thereafter sign-in resolution."""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pyisemail import is_email

from backend.config import config
from backend.models.provisioned_account_entry import VALID_ROLES, ProvisionedAccountEntry
from backend.services.cosmos_service import CosmosService
from backend.services.entra_directory_service import EntraDirectoryService

logger = logging.getLogger("account_provisioning_service")
# #165 Scenario 6 live check: this comment is the "one testable file"
# bundled alongside the docs-only commit on this branch, to confirm the
# full pipeline runs once any code file is touched (FR-020).


class InvalidEmailError(ValueError):
    """Raised when an email fails RFC 5322 validation (FR-005)."""


class RoleRequiredError(ValueError):
    """Raised when no valid role is supplied (FR-003/FR-004)."""


class SelfRemovalError(ValueError):
    """Raised when an administrator attempts to remove their own account (FR-012)."""


class SeedAdminRemovalError(ValueError):
    """Raised when removal targets the seed administrator's account (FR-012)."""


class AccountNotFoundError(ValueError):
    """Raised when no provisioned entry exists for the removal target."""


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AccountProvisioningService:
    """Looks up, binds, adds, merges, and lists Provisioned Account Entries."""

    def __init__(
        self,
        cosmos_service: Optional[CosmosService] = None,
        entra_directory_service: Optional[EntraDirectoryService] = None,
    ) -> None:
        self._cosmos = cosmos_service or CosmosService()
        self._entra = entra_directory_service or EntraDirectoryService()

    def get_by_email(self, email: str) -> Optional[ProvisionedAccountEntry]:
        """Point read by lowercased email."""
        email = email.lower()
        container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
        try:
            item = container.read_item(item=email, partition_key=email)
        except CosmosResourceNotFoundError:
            return None
        return ProvisionedAccountEntry.from_dict(item)

    def authorize_sign_in(self, email: Optional[str], oid: str) -> tuple[bool, Optional[ProvisionedAccountEntry]]:
        """Resolve a sign-in by email, then bind or verify the token's oid (FR-006/FR-007).

        Returns (is_authorized, entry). No email claim on the token, or no entry for it,
        -> (False, None). Unbound entry -> bind oid, persist, and allow. Matching bound
        oid -> allow. Mismatched bound oid -> deny.
        """
        if email is None:
            # Entra ID's `email` claim isn't guaranteed present on every token
            # (varies by app registration/account type) — treat a missing
            # claim the same as "no provisioned entry" rather than crashing
            # inside get_by_email's unconditional email.lower().
            logger.info("Sign-in denied: token carried no email claim")
            return False, None

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

        self._entra.invite_guest(normalized_email)

        return entry

    def list_all(self) -> list[ProvisionedAccountEntry]:
        """Return every Provisioned Account Entry (FR-010)."""
        results = self._cosmos.query(
            config.PROVISIONED_ACCOUNTS_CONTAINER,
            "SELECT * FROM c WHERE c.entityType = 'ProvisionedAccountEntry'",
        )
        return [ProvisionedAccountEntry.from_dict(row) for row in results]

    def remove_account(self, email: str, requested_by_email: str, seed_admin_email: str) -> None:
        """Remove a Provisioned Account Entry and its Entra guest user (FR-012/FR-013).

        Rejects removal of the signed-in administrator's own email or the
        deployment-configured seed administrator's email. Raises
        AccountNotFoundError if no entry exists for the target email. On
        success, deletes the Cosmos entry and calls EntraDirectoryService.remove_guest
        (a no-op if no matching guest is found).
        """
        normalized_email = email.lower()

        if normalized_email == (requested_by_email or "").lower():
            raise SelfRemovalError(f"{email!r} is the requesting administrator's own account")
        if seed_admin_email and normalized_email == seed_admin_email.lower():
            raise SeedAdminRemovalError(f"{email!r} is the seed administrator's account")

        if self.get_by_email(normalized_email) is None:
            raise AccountNotFoundError(f"No provisioned account entry exists for {email!r}")

        container = self._cosmos.get_container(config.PROVISIONED_ACCOUNTS_CONTAINER)
        container.delete_item(item=normalized_email, partition_key=normalized_email)

        self._entra.remove_guest(normalized_email)
        logger.info("Account removed", extra={"email": normalized_email})
