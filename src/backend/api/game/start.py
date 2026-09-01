"""Game start endpoint — validates a completed setup (adventure, character name, character
type) server-side per Constitution Principle II (006-adventure-and-character-setup,
contracts/api.md). Does not create a play session; that's 008-core-gameplay's responsibility
(research.md Decision 4)."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from backend.api.game.middleware import authorize_player
from backend.api.utils import error_response, json_response
from backend.services.account_provisioning_service import AccountProvisioningService
from backend.services.story_service import StoryService

logger = logging.getLogger("game.start")

MAX_CHARACTER_NAME_LENGTH = 50

FIELD_MESSAGES = {
    "adventureId": "Select an adventure.",
    "characterName_required": "Character name is required.",
    "characterName_too_long": f"Character name must be {MAX_CHARACTER_NAME_LENGTH} characters or fewer.",
    "characterType_required": "Select a character type for this adventure.",
    "characterType_invalid": "Choose one of this adventure's character types.",
}


def _body(req: func.HttpRequest) -> dict:
    try:
        return json.loads(req.get_body() or b"{}")
    except (ValueError, json.JSONDecodeError):
        return {}


def start(
    req: func.HttpRequest,
    account_provisioning_service: AccountProvisioningService | None = None,
    story_service: StoryService | None = None,
) -> func.HttpResponse:
    is_authorized, user_oid, error = authorize_player(req, account_provisioning_service=account_provisioning_service)
    if not is_authorized:
        return error

    body = _body(req)
    adventure_id = body.get("adventureId")
    character_name = body.get("characterName")
    character_type = body.get("characterType")

    if not adventure_id:
        return _invalid_setup({"adventureId": FIELD_MESSAGES["adventureId"]})

    service = story_service or StoryService()
    story = service.get_story(adventure_id)
    if story is None or not story.published:
        return error_response(404, "not_found", "Adventure not found")

    fields: dict[str, str] = {}

    trimmed_name = (character_name or "").strip()
    if not trimmed_name:
        fields["characterName"] = FIELD_MESSAGES["characterName_required"]
    elif len(trimmed_name) > MAX_CHARACTER_NAME_LENGTH:
        fields["characterName"] = FIELD_MESSAGES["characterName_too_long"]

    valid_type_names = {ct.name for ct in story.characterTypes}
    if not character_type:
        fields["characterType"] = FIELD_MESSAGES["characterType_required"]
    elif character_type not in valid_type_names:
        fields["characterType"] = FIELD_MESSAGES["characterType_invalid"]

    if fields:
        return _invalid_setup(fields)

    logger.info("Game setup validated", extra={"user_oid": user_oid, "adventure_id": adventure_id})
    return json_response(
        {
            "status": "success",
            "adventureId": adventure_id,
            "characterName": trimmed_name,
            "characterType": character_type,
        },
        status_code=200,
    )


def _invalid_setup(fields: dict[str, str]) -> func.HttpResponse:
    return json_response(
        {
            "error": "invalid_setup",
            "message": "Setup is incomplete or invalid.",
            "fields": fields,
        },
        status_code=400,
    )
