"""Admin sessions endpoints — the list of every gameplay session, real player and admin
test-play alike (026-token-usage contracts/api.md → GET /api/manage/sessions), and the
administrator delete of one of them (031-sessions-admin-design-spec contracts/api.md →
DELETE /api/manage/sessions/{sessionId}, superseding 026-token-usage FR-016)."""

from __future__ import annotations

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import error_response, json_response
from backend.services.session_overview_service import SessionNotFoundError, SessionOverviewService


def list_sessions(
    req: func.HttpRequest,
    session_overview_service: SessionOverviewService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    service = session_overview_service or SessionOverviewService()
    return json_response({"status": "success", "sessions": service.list_sessions()}, status_code=200)


def delete_session(
    req: func.HttpRequest,
    session_overview_service: SessionOverviewService | None = None,
) -> func.HttpResponse:
    """Permanently deletes one session and everything on it — its saved progress and its
    transcript (FR-008). Never touches the story it belongs to, so no story's cumulative
    token total is decremented (FR-009)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    session_id = req.route_params.get("sessionId")
    service = session_overview_service or SessionOverviewService()
    try:
        service.delete_session(session_id)
    except SessionNotFoundError:
        return error_response(404, "not_found", "Session not found")

    return json_response({"status": "deleted", "sessionId": session_id}, status_code=200)
