"""Administrator test-play endpoints (010-story-test-play-done, contracts/api.md) — start a
session against a story's current saved configuration (works on an unpublished story),
submit an instruction, delete/abort, and rehydrate a session on refresh."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import error_response, json_response
from backend.services.test_play_session_service import (
    ForbiddenError,
    InteractionInProgressError,
    InvalidInputError,
    NarrativeUnavailableError,
    RateLimitedError,
    SessionConcludedError,
    SessionNotFoundError,
    StoryNotFoundError,
    TestPlaySessionService,
)

logger = logging.getLogger("admin.test_play")


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


def start_test_play(
    req: func.HttpRequest,
    test_play_session_service: TestPlaySessionService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = test_play_session_service or TestPlaySessionService()
    try:
        session = service.create_session(story_id=story_id, administrator_id=user_oid)
    except StoryNotFoundError:
        return error_response(404, "not_found", "Story not found")
    except NarrativeUnavailableError:
        return error_response(502, "narrative_unavailable", "Couldn't generate the opening narrative. Please try again.")

    return json_response(
        {
            "status": "success",
            "sessionId": session.id,
            "characterType": session.characterType,
            "narrative": _narrative_dict(session.turns[0]),
        },
        status_code=201,
    )


def submit_test_play_interaction(
    req: func.HttpRequest,
    test_play_session_service: TestPlaySessionService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    body = _body(req)

    service = test_play_session_service or TestPlaySessionService()
    try:
        session, completion_reason = service.submit_exchange(
            session_id=session_id, administrator_id=user_oid, raw_input=body.get("input")
        )
    except InvalidInputError:
        return error_response(400, "invalid_input", "Type an action to continue.")
    except ForbiddenError:
        return error_response(403, "access_denied", "Access not granted")
    except (SessionNotFoundError, StoryNotFoundError):
        return error_response(404, "not_found", "Session not found")
    except SessionConcludedError:
        return error_response(409, "session_concluded", "This test session has already ended.")
    except InteractionInProgressError:
        return error_response(409, "interaction_in_progress", "Your last action is still being processed.")
    except RateLimitedError:
        return error_response(429, "rate_limited", "Slow down a little — take a breath before your next move.")
    except NarrativeUnavailableError:
        return error_response(502, "narrative_unavailable", "Couldn't generate the next turn. Please try again.")

    body_out: dict = {"status": session.status, "narrative": _narrative_dict(session.turns[-1])}
    if completion_reason is not None:
        body_out["completionReason"] = completion_reason
    return json_response(body_out, status_code=200)


def delete_test_play_session(
    req: func.HttpRequest,
    test_play_session_service: TestPlaySessionService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    service = test_play_session_service or TestPlaySessionService()
    try:
        service.delete_session(session_id=session_id, administrator_id=user_oid)
    except ForbiddenError:
        return error_response(403, "access_denied", "Access not granted")

    return json_response({"status": "deleted", "sessionId": session_id}, status_code=200)


def get_test_play_session(
    req: func.HttpRequest,
    test_play_session_service: TestPlaySessionService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    service = test_play_session_service or TestPlaySessionService()
    try:
        session = service.get_session(session_id=session_id, administrator_id=user_oid)
    except ForbiddenError:
        return error_response(403, "access_denied", "Access not granted")
    except SessionNotFoundError:
        return error_response(404, "not_found", "Session not found")

    return json_response({"status": "success", "session": session.to_dict()}, status_code=200)
