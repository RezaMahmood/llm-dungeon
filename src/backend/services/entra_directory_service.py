"""Microsoft Graph client for Entra ID guest-user lifecycle — invites a
provisioned account's email as a tenant guest on grant (FR-011), and removes
that guest user on account removal (FR-013)."""

from __future__ import annotations

import logging
from typing import Optional

import requests
from azure.identity import DefaultAzureCredential

from backend.config import config

logger = logging.getLogger("entra_directory_service")

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_GRAPH_SCOPE = "https://graph.microsoft.com/.default"
_REQUEST_TIMEOUT_SECONDS = 10


def _escape_odata_literal(value: str) -> str:
    """Escape a single-quoted OData string literal (doubling embedded quotes)."""
    return value.replace("'", "''")


class EntraDirectoryService:
    """Thin wrapper around the Microsoft Graph REST API, authenticated via
    Managed Identity (Constitution Principle VII), matching CosmosService's
    lazy-credential construction pattern."""

    def __init__(
        self,
        credential: Optional[DefaultAzureCredential] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._credential = credential
        self._session = session or requests.Session()

    @property
    def credential(self) -> DefaultAzureCredential:
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def _headers(self) -> dict[str, str]:
        token = self.credential.get_token(_GRAPH_SCOPE).token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _find_user_id(self, email: str) -> Optional[str]:
        response = self._session.get(
            f"{_GRAPH_BASE_URL}/users",
            headers=self._headers(),
            params={"$filter": f"mail eq '{_escape_odata_literal(email)}'", "$select": "id"},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json().get("value", [])
        return results[0]["id"] if results else None

    def invite_guest(self, email: str) -> None:
        """Invite `email` as a tenant guest. No-op if already a tenant member."""
        if self._find_user_id(email) is not None:
            logger.info("Entra guest invite skipped: already a tenant member", extra={"email": email})
            return

        response = self._session.post(
            f"{_GRAPH_BASE_URL}/invitations",
            headers=self._headers(),
            json={
                "invitedUserEmailAddress": email,
                "inviteRedirectUrl": config.FRONTEND_URL,
                "sendInvitationMessage": True,
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        logger.info("Entra guest invited", extra={"email": email})

    def remove_guest(self, email: str) -> None:
        """Remove `email`'s tenant guest user. No-op if no matching guest is found."""
        user_id = self._find_user_id(email)
        if user_id is None:
            logger.info("Entra guest removal skipped: no matching guest found", extra={"email": email})
            return

        response = self._session.delete(
            f"{_GRAPH_BASE_URL}/users/{user_id}",
            headers=self._headers(),
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        logger.info("Entra guest removed", extra={"email": email})
