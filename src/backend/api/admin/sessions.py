"""Admin sessions endpoint — a read-only list of every gameplay session, real player and
admin test-play alike (026-token-usage contracts/api.md → GET /api/manage/sessions)."""

from __future__ import annotations

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import json_response
from backend.services.session_overview_service import SessionOverviewService


def list_sessions(
    req: func.HttpRequest,
    session_overview_service: SessionOverviewService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    service = session_overview_service or SessionOverviewService()
    return json_response({"status": "success", "sessions": service.list_sessions()}, status_code=200)
