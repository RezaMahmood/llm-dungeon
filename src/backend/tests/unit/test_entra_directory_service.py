"""Unit tests for EntraDirectoryService (mocked Graph HTTP client)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.entra_directory_service import EntraDirectoryService

EMAIL = "player@example.com"


def _service_with_session():
    credential = MagicMock()
    credential.get_token.return_value = MagicMock(token="fake-graph-token")
    session = MagicMock()
    return EntraDirectoryService(credential=credential, session=session), session


def _users_response(results):
    response = MagicMock()
    response.json.return_value = {"value": results}
    return response


# --- invite_guest ---


def test_invite_guest_creates_invitation_when_not_a_tenant_member():
    service, session = _service_with_session()
    session.get.return_value = _users_response([])
    session.post.return_value = MagicMock()

    service.invite_guest(EMAIL)

    session.post.assert_called_once()
    _args, kwargs = session.post.call_args
    assert kwargs["json"]["invitedUserEmailAddress"] == EMAIL


def test_invite_guest_is_a_noop_when_already_a_tenant_member():
    service, session = _service_with_session()
    session.get.return_value = _users_response([{"id": "existing-user-id"}])

    service.invite_guest(EMAIL)

    session.post.assert_not_called()


def test_invite_guest_filters_by_email_and_escapes_quotes():
    service, session = _service_with_session()
    session.get.return_value = _users_response([])
    session.post.return_value = MagicMock()

    service.invite_guest("o'brien@example.com")

    _args, kwargs = session.get.call_args
    assert kwargs["params"]["$filter"] == "mail eq 'o''brien@example.com'"


# --- remove_guest ---


def test_remove_guest_deletes_the_matching_user():
    service, session = _service_with_session()
    session.get.return_value = _users_response([{"id": "existing-user-id"}])
    session.delete.return_value = MagicMock()

    service.remove_guest(EMAIL)

    session.delete.assert_called_once()
    args, _kwargs = session.delete.call_args
    assert args[0].endswith("/users/existing-user-id")


def test_remove_guest_is_a_noop_when_no_matching_guest_is_found():
    service, session = _service_with_session()
    session.get.return_value = _users_response([])

    service.remove_guest(EMAIL)

    session.delete.assert_not_called()
