"""Player-facing adventure listing/detail endpoints (006-adventure-and-character-setup,
contracts/api.md). Published stories only — see StoryService.list_published_summaries."""

from __future__ import annotations

import azure.functions as func

from backend.api.game.middleware import authorize_player
from backend.api.utils import error_response, json_response
from backend.services.account_provisioning_service import AccountProvisioningService
from backend.services.story_service import StoryService

NOT_FOUND_MESSAGE = "Adventure not found"


def list_adventures(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    service = story_service or StoryService()
    adventures = service.list_published_summaries()
    return json_response({"status": "success", "adventures": adventures}, status_code=200)


def get_adventure(
    req: func.HttpRequest,
    story_service: StoryService | None = None,
    account_provisioning_service: AccountProvisioningService | None = None,
) -> func.HttpResponse:
    is_authorized, _user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    adventure_id = req.route_params.get("adventureId")
    service = story_service or StoryService()
    story = service.get_story(adventure_id) if adventure_id else None

    if story is None or not story.published:
        return error_response(404, "not_found", NOT_FOUND_MESSAGE)

    return json_response(
        {
            "status": "success",
            "adventure": {
                "id": story.id,
                "name": story.name,
                "characterTypes": [ct.to_dict() for ct in story.characterTypes],
            },
        },
        status_code=200,
    )
