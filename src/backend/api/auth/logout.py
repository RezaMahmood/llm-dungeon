"""POST /api/auth/logout — stateless backend signal; frontend clears MSAL cache."""

from __future__ import annotations

import azure.functions as func

from backend.api.auth.middleware import authenticate
from backend.api.utils import json_response, unauthorized


def logout(req: func.HttpRequest) -> func.HttpResponse:
    is_valid, _user_oid, error = authenticate(req)
    if not is_valid:
        return unauthorized(error)

    return json_response({"message": "Logged out successfully"}, status_code=200)
