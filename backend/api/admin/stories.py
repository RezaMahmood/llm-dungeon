"""Admin story endpoints — placeholders; full implementation lands in 005/012."""

from __future__ import annotations

import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import json_response

logger = logging.getLogger("admin.stories")


def create_story(req: func.HttpRequest) -> func.HttpResponse:
    is_authorized, user_oid, error_response = authorize_admin(req)
    if not is_authorized:
        return error_response

    logger.info("Admin story create placeholder invoked", extra={"user_oid": user_oid})
    return json_response({"status": "success", "message": "Story creation not yet implemented"}, status_code=200)


def list_stories(req: func.HttpRequest) -> func.HttpResponse:
    is_authorized, user_oid, error_response = authorize_admin(req)
    if not is_authorized:
        return error_response

    logger.info("Admin story list placeholder invoked", extra={"user_oid": user_oid})
    return json_response({"status": "success", "stories": []}, status_code=200)
