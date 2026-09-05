"""Play session endpoints — create a session (superseding game/start's role), submit an
interaction, and resume a player's own session (008-core-gameplay, contracts/api.md)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.game.middleware import authorize_player
from backend.api.utils import error_response, forbidden_access_not_granted, json_response
from backend.services.account_provisioning_service import AccountProvisioningService
from backend.services.play_session_service import (
    AdventureNotFoundError,
    AlreadyActiveError,
    ContentSafetyLockoutError,
    ForbiddenError,
    InteractionInProgressError,
    InvalidInputError,
    InvalidSetupError,
    NarrativeUnavailableError,
    PlaySessionService,
    RateLimitedError,
    SessionConcludedError,
    SessionInactiveError,
    SessionNotFoundError,
)

logger = logging.getLogger("game.sessions")


def _body(req: func.HttpRequest) -> dict:
    try:
        return json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def _narrative_dict(turn) -> dict:
    return {
        "turnNumber": turn.turnNumber,
        "narrativeText": turn.narrativeText,
        "suggestedActions": turn.suggestedActions,
        "locationLabel": turn.locationLabel,
        "goalLabel": turn.goalLabel,
        "progress": turn.progress,
    }


def _lockout_response(exc: ContentSafetyLockoutError) -> func.HttpResponse:
    return error_response(
        423,
        "content_safety_lockout",
        f"You're temporarily locked out due to repeated flagged submissions. Try again after {exc.lockout_until}.",
    )


def create_session(
    req: func.HttpRequest,
    play_session_service: PlaySessionService | None = None,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    body = _body(req)
    service = play_session_service or PlaySessionService()

    try:
        session = service.create_session(
            adventure_id=body.get("adventureId"),
            character_name=body.get("characterName"),
            character_type=body.get("characterType"),
            player_id=user_oid,
        )
    except ContentSafetyLockoutError as exc:
        return _lockout_response(exc)
    except AdventureNotFoundError:
        return error_response(404, "not_found", "Adventure not found")
    except InvalidSetupError as exc:
        return json_response(
            {"error": "invalid_setup", "message": "Setup is incomplete or invalid.", "fields": exc.fields},
            status_code=400,
        )
    except NarrativeUnavailableError:
        return error_response(502, "narrative_unavailable", "Couldn't generate the opening narrative. Please try again.")

    return json_response(
        {"status": "success", "sessionId": session.id, "narrative": _narrative_dict(session.turns[0])},
        status_code=201,
    )


def submit_interaction(
    req: func.HttpRequest,
    play_session_service: PlaySessionService | None = None,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    body = _body(req)

    service = play_session_service or PlaySessionService()
    try:
        session, completion_reason = service.submit_interaction(
            session_id=session_id, player_id=user_oid, raw_input=body.get("input")
        )
    except ContentSafetyLockoutError as exc:
        return _lockout_response(exc)
    except InvalidInputError:
        return error_response(400, "invalid_input", "Type an action to continue.")
    except SessionNotFoundError:
        return error_response(404, "not_found", "Session not found")
    except ForbiddenError:
        return forbidden_access_not_granted()
    except SessionInactiveError:
        return error_response(409, "session_inactive", "You left this story to play another. Resume it to continue here.")
    except SessionConcludedError:
        return error_response(409, "session_concluded", "This story has already ended.")
    except RateLimitedError:
        return error_response(429, "rate_limited", "Slow down a little — take a breath before your next move.")
    except InteractionInProgressError:
        return error_response(409, "interaction_in_progress", "Your last action is still being processed.")
    except NarrativeUnavailableError:
        return error_response(502, "narrative_unavailable", "Couldn't generate the next turn. Please try again.")

    body_out: dict = {"status": session.status, "narrative": _narrative_dict(session.turns[-1])}
    if completion_reason is not None:
        body_out["completionReason"] = completion_reason
    return json_response(body_out, status_code=200)


def resume_session(
    req: func.HttpRequest,
    play_session_service: PlaySessionService | None = None,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    service = play_session_service or PlaySessionService()
    try:
        session = service.resume_session(session_id=session_id, player_id=user_oid)
    except SessionNotFoundError:
        return error_response(404, "not_found", "Session not found")
    except ForbiddenError:
        return forbidden_access_not_granted()
    except SessionConcludedError:
        return error_response(409, "session_concluded", "This story has already ended.")
    except AlreadyActiveError:
        return error_response(409, "already_active", "This is already your active story.")

    return json_response({"status": "active", "sessionId": session.id}, status_code=200)
