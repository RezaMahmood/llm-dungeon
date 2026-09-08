"""Admin story endpoints — guided story-creation drafts and the stories they generate
(contracts/api.md)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.admin.middleware import authorize_admin
from backend.api.utils import error_response, json_response, raw_json_response
from backend.services import story_config_file
from backend.services.story_config_file import InvalidStoryConfigurationError
from backend.services.story_draft_service import (
    DraftIncompleteError,
    DraftNotFoundError,
    DraftValidationError,
    GenerationFailedError,
    LLMRateLimitedError,
    StoryDraftService,
    WrongDraftModeError,
)
from backend.services.story_service import (
    PUBLISH_GATE_NOT_SATISFIED,
    ConfirmationRequiredError,
    ContentGenerationFailedError,
    ContentGenerationRateLimitedError,
    StaleStoryError,
    StoryNotFoundError,
    StoryService,
    TitleRequiredError,
    WriteConflictError,
)

logger = logging.getLogger("admin.stories")

GENERATION_FAILED_MESSAGE = "Story generation did not produce a usable configuration; please try again"
RATE_LIMITED_MESSAGE = "The story-generation service is temporarily busy; please try again shortly"
NOT_READY_MESSAGE = "name, worldPrompt, characterTypes, and completionCriteria are all required before generating"
TEST_PLAY_REQUIRED_MESSAGE = "This story must be test-played since its last content change before it can be published."
NOT_READY_SAVE_MESSAGE = "name, worldPrompt, characterTypes, and completionCriteria are all required before saving"
STALE_STORY_MESSAGE = "This story changed since you opened it. Reload it and reapply your change."
WRITE_CONFLICT_MESSAGE = "Another change to this story landed at the same time. Try again."
WRONG_DRAFT_MODE_NOT_EDIT_MESSAGE = "This draft is not an edit of an existing story"
WRONG_DRAFT_MODE_IS_EDIT_MESSAGE = "This draft is an edit of an existing story"
CONFIRMATION_REQUIRED_MESSAGE = "Confirm the story this file will overwrite before uploading."
TITLE_REQUIRED_MESSAGE = "A title is required to create a new story from this file."
STORY_NOT_FOUND_IMPORT_MESSAGE = "No story exists with the id in this file. Remove the id to upload it as a new story."


def _body(req: func.HttpRequest) -> dict:
    try:
        return json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def _draft_write_response(draft) -> func.HttpResponse:
    return json_response(
        {"status": "success", "draft": draft.to_dict(), "readyToGenerate": draft.is_complete()}, status_code=200
    )


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
        draft = service.patch_draft(draft_id, _body(req))
    except DraftValidationError as exc:
        return error_response(422, "invalid_field", str(exc))

    if draft is None:
        return error_response(404, "not_found", "Draft not found")

    return _draft_write_response(draft)


def suggest_world_prompt(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    """One pass over the administrator's idea, writing only `worldPrompt` (#227) — there
    is no conversation to append to and no other field is touched."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    idea = _body(req).get("idea", "")
    service = story_draft_service or StoryDraftService()
    try:
        draft = service.suggest_world_prompt(draft_id, idea)
    except LLMRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    if draft is None:
        return error_response(404, "not_found", "Draft not found")

    return _draft_write_response(draft)


def generate_story_from_draft(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    """The administrator's explicit "finish" action — never triggered automatically by a
    field write (#33)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    service = story_draft_service or StoryDraftService()
    try:
        story = service.generate_story(draft_id)
    except WrongDraftModeError:
        return error_response(422, "wrong_draft_mode", WRONG_DRAFT_MODE_IS_EDIT_MESSAGE)
    except DraftIncompleteError:
        return error_response(422, "not_ready", NOT_READY_MESSAGE)
    except GenerationFailedError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)
    except LLMRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    if story is None:
        return error_response(404, "not_found", "Draft not found")

    return json_response({"status": "generated", "storyId": story.id, "story": story.to_dict()}, status_code=200)


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


def publish_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = story_service or StoryService()
    result = service.publish(story_id)
    if result is None:
        return error_response(404, "not_found", "Story not found")
    if result is PUBLISH_GATE_NOT_SATISFIED:
        return error_response(409, "test_play_required", TEST_PLAY_REQUIRED_MESSAGE)

    return json_response({"status": "success", "story": result.to_dict()}, status_code=200)


def unpublish_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = story_service or StoryService()
    result = service.unpublish(story_id)
    if result is None:
        return error_response(404, "not_found", "Story not found")

    return json_response({"status": "success", "story": result.to_dict()}, status_code=200)


def get_story_configuration(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """The story's complete configuration file, byte-for-byte what the viewer and the
    download both use (FR-002, FR-004, contracts/api.md)."""
    is_authorized, _user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    service = story_service or StoryService()
    story = service.get_story(story_id)
    if story is None:
        return error_response(404, "not_found", "Story not found")

    return raw_json_response(story_config_file.serialize(story), status_code=200)


def create_edit_draft(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    """Reopen an existing story in the wizard (FR-003) — never blocked by publish state or
    the test-play gate."""
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    story_id = req.route_params.get("storyId")
    stories = story_service or StoryService()
    story = stories.get_story(story_id)
    if story is None:
        return error_response(404, "not_found", "Story not found")

    drafts = story_draft_service or StoryDraftService(story_service=stories)
    draft = drafts.create_edit_draft(story, user_oid)
    return json_response(
        {"status": "success", "draft": draft.to_dict(), "readyToGenerate": draft.is_complete()}, status_code=201
    )


def save_draft(
    req: func.HttpRequest,
    story_draft_service: StoryDraftService | None = None,
) -> func.HttpResponse:
    """Edit mode's terminal action — applies the draft back to its source story
    (FR-003, FR-006, FR-009)."""
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    draft_id = req.route_params.get("draftId")
    service = story_draft_service or StoryDraftService()
    try:
        story = service.save_draft_to_story(draft_id, user_oid)
    except WrongDraftModeError:
        return error_response(422, "wrong_draft_mode", WRONG_DRAFT_MODE_NOT_EDIT_MESSAGE)
    except DraftIncompleteError:
        return error_response(422, "not_ready", NOT_READY_SAVE_MESSAGE)
    except StaleStoryError:
        return error_response(409, "stale_story", STALE_STORY_MESSAGE)
    except WriteConflictError:
        return error_response(409, "write_conflict", WRITE_CONFLICT_MESSAGE)
    except DraftNotFoundError as exc:
        return error_response(404, "not_found", str(exc))
    except ContentGenerationFailedError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)
    except ContentGenerationRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    if story is None:
        return error_response(404, "not_found", "Draft not found")

    return json_response({"status": "saved", "storyId": story.id, "story": story.to_dict()}, status_code=200)


def import_story(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    """Re-upload a configuration file (FR-005) — an id-matched file overwrites that story,
    an id-less file creates a new one (contracts/api.md → POST …/import)."""
    is_authorized, user_oid, error = authorize_admin(req)
    if not is_authorized:
        return error

    body = _body(req)
    configuration_text = body.get("configurationText", "")
    try:
        configuration = story_config_file.parse_text(configuration_text)
    except InvalidStoryConfigurationError as exc:
        return error_response(422, "invalid_configuration", str(exc))

    service = story_service or StoryService()
    try:
        outcome, story = service.import_configuration(
            configuration,
            admin_oid=user_oid,
            confirm_overwrite_story_id=body.get("confirmOverwriteStoryId"),
            title=body.get("title"),
        )
    except ConfirmationRequiredError:
        return error_response(422, "confirmation_required", CONFIRMATION_REQUIRED_MESSAGE)
    except TitleRequiredError:
        return error_response(422, "title_required", TITLE_REQUIRED_MESSAGE)
    except StoryNotFoundError:
        return error_response(404, "story_not_found", STORY_NOT_FOUND_IMPORT_MESSAGE)
    except WriteConflictError:
        return error_response(409, "write_conflict", WRITE_CONFLICT_MESSAGE)
    except ContentGenerationFailedError:
        return error_response(502, "generation_failed", GENERATION_FAILED_MESSAGE)
    except ContentGenerationRateLimitedError:
        return error_response(429, "rate_limited", RATE_LIMITED_MESSAGE)

    status_code = 200 if outcome == "updated" else 201
    return json_response({"status": outcome, "storyId": story.id, "story": story.to_dict()}, status_code=status_code)
