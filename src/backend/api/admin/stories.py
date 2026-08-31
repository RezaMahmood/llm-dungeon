"""Admin story endpoints — explicit Save/Abandon Story persistence, cover-image upload,
Tab 02's one-shot outline suggestion, and story listing (Session 2026-08-30 redesign)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.auth.middleware import authenticate_with_email
from backend.api.utils import error_response, json_response
from backend.services.llm_service import LLMOutputError, LLMService
from backend.services.story_service import StoryService, StoryValidationError

logger = logging.getLogger("admin.stories")

GENERATION_FAILED_MESSAGE = "Could not generate a suggested outline right now; please try again"


def _body(req: func.HttpRequest) -> dict:
    try:
        return json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def _admin_email(req: func.HttpRequest) -> str | None:
    # authorize_admin already validated the token/authorization; re-reading the email
    # claim here avoids widening authorize_admin's shared return shape (matches
    # admin/accounts.py's pattern). Needed for Story.createdBy/updatedBy (FR-012).
    _is_valid, _oid, email, _error = authenticate_with_email(req)
    return email


def create_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """Save (first write) — creates a new Story record (FR-004). `name` is required;
    every other field is optional (FR-009)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    body = _body(req)
    name = body.get("name")
    admin_email = _admin_email(req)

    service = story_service or StoryService()
    try:
        story = service.create_story(name, admin_email, body)
    except StoryValidationError as exc:
        return error_response(422, "invalid_field", str(exc))

    logger.info("Story created", extra={"story_id": story.id})
    return json_response({"status": "success", "story": story.to_dict()}, status_code=201)


def update_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """Save (later write) — updates an existing Story record in place (FR-004)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    admin_email = _admin_email(req)
    service = story_service or StoryService()
    try:
        story = service.update_story(story_id, admin_email, _body(req))
    except StoryValidationError as exc:
        return error_response(422, "invalid_field", str(exc))

    if story is None:
        return error_response(404, "not_found", "Story not found")

    return json_response({"status": "success", "story": story.to_dict()}, status_code=200)


def delete_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """Abandon (FR-013/014) — deletes the Story record if one was ever saved; a no-op,
    not an error, when nothing exists yet for this id (Edge Cases)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = story_service or StoryService()
    service.delete_story(story_id)

    return json_response({"status": "success"}, status_code=200)


def upload_cover_image(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """Uploads a Tab 01 cover image to blob storage and stores the reference on the Story
    (FR-009). The story must already exist (i.e. Save has created it) — the wizard always
    performs the field Save before this call, so this endpoint doesn't itself create a
    story from just a name-less image upload."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    admin_email = _admin_email(req)
    filename = req.headers.get("X-File-Name") or "cover"
    content_type = req.headers.get("Content-Type")

    service = story_service or StoryService()
    story = service.upload_cover_image(story_id, admin_email, filename, req.get_body(), content_type)
    if story is None:
        return error_response(404, "not_found", "Story not found")

    return json_response({"status": "success", "story": story.to_dict()}, status_code=200)


def suggest_outline(
    req: func.HttpRequest,
    llm_service: LLMService | None = None,
) -> func.HttpResponse:
    """Tab 02's one-shot "Suggest" action (FR-003) — no story needs to exist yet."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    idea = _body(req).get("idea", "")
    if not idea:
        return error_response(422, "invalid_field", "idea is required")

    service = llm_service or LLMService()
    try:
        outline = service.suggest_outline(idea)
    except LLMOutputError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)

    return json_response({"status": "success", "outline": outline}, status_code=200)


def list_stories(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    service = story_service or StoryService()
    return json_response({"status": "success", "stories": service.list_summaries()}, status_code=200)


def get_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = story_service or StoryService()
    story = service.get_story(story_id)
    if story is None:
        return error_response(404, "not_found", "Story not found")

    return json_response({"status": "success", "story": story.to_dict()}, status_code=200)
