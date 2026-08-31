"""Admin story endpoints — guided story-creation drafts and the stories they generate
(contracts/api.md)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import error_response, json_response
from backend.services.story_draft_service import (
    DraftValidationError,
    GenerationFailedError,
    LLMRateLimitedError,
    StoryDraftService,
)
from backend.services.story_service import StoryService

logger = logging.getLogger("admin.stories")

GENERATION_FAILED_MESSAGE = "Story generation did not produce a usable configuration; please try again"
RATE_LIMITED_MESSAGE = "The story-generation service is temporarily busy; please try again shortly"


def _body(req: func.HttpRequest) -> dict:
    try:
        return json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def _draft_write_response(draft, story) -> func.HttpResponse:
    if story is not None:
        return json_response({"status": "generated", "storyId": story.id, "story": story.to_dict()}, status_code=200)
    return json_response({"status": "success", "draft": draft.to_dict(), "readyToGenerate": False}, status_code=200)


def create_draft(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    idea = _body(req).get("idea")
    service = story_draft_service or StoryDraftService()
    try:
        draft = service.create_draft(created_by=user_oid, idea=idea)
    except LLMRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    logger.info("Story draft created", extra={"draft_id": draft.id, "user_oid": user_oid})
    return json_response({"status": "success", "draft": draft.to_dict()}, status_code=201)


def get_draft(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    service = story_draft_service or StoryDraftService()
    draft = service.get_draft(draft_id)
    if draft is None:
        return error_response(404, "not_found", "Draft not found")

    return json_response({"status": "success", "draft": draft.to_dict()}, status_code=200)


def patch_draft(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    service = story_draft_service or StoryDraftService()
    try:
        draft, story = service.patch_draft(draft_id, _body(req))
    except DraftValidationError as exc:
        return error_response(422, "invalid_field", str(exc))
    except GenerationFailedError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)
    except LLMRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    if draft is None:
        return error_response(404, "not_found", "Draft not found")

    return _draft_write_response(draft, story)


def post_message(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    message = _body(req).get("message", "")
    service = story_draft_service or StoryDraftService()
    try:
        draft, story = service.post_message(draft_id, message)
    except GenerationFailedError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)
    except LLMRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    if draft is None:
        return error_response(404, "not_found", "Draft not found")

    return _draft_write_response(draft, story)


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
