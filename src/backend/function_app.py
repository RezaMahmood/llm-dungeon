"""Azure Functions app entry point — registers HTTP routes for auth, admin, and game APIs."""

import logging
import os

import azure.functions as func
from azure.monitor.opentelemetry import configure_azure_monitor

from backend.api.admin.accounts import add_account, list_accounts, remove_account
from backend.api.admin.stories import (
    create_draft,
    generate_story_from_draft,
    get_draft,
    get_story,
    list_stories,
    patch_draft,
    post_message,
    publish_story,
    unpublish_story,
)
from backend.api.auth.login import login
from backend.api.auth.logout import logout
from backend.api.auth.me import me
from backend.api.game.adventures import get_adventure, list_adventures
from backend.api.game.start import start
from backend.api.utils import server_error
from backend.config import config
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("function_app")

# Principle VI (Observability & AI Cost Transparency, NON-NEGOTIABLE) — one-call
# OpenTelemetry -> Application Insights wiring, initialized once at startup so
# every later span (e.g. llm_service.py's gen_ai.* spans) is exported.
# APPLICATIONINSIGHTS_CONNECTION_STRING is supplied as an Azure Functions
# application setting by 007-azure-infrastructure-provisioning, same as
# config.py's Azure AD / Cosmos settings — not present locally, where this
# step is skipped (configure_azure_monitor() raises rather than no-opping
# if it's absent).
if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

if config.SEED_ADMIN_EMAIL:
    AccountProvisioningService().ensure_seed_administrator(config.SEED_ADMIN_EMAIL)


def _guarded(handler):
    def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        try:
            return handler(req)
        except Exception:  # noqa: BLE001 - convert unexpected errors to a generic 500
            logger.exception("Unhandled error in %s", handler.__name__)
            return server_error()

    return wrapper


@app.route(route="auth/login", methods=["POST"])
def auth_login(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(login)(req)


@app.route(route="auth/me", methods=["GET"])
def auth_me(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(me)(req)


@app.route(route="auth/logout", methods=["POST"])
def auth_logout(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(logout)(req)


@app.route(route="manage/stories/drafts", methods=["POST"])
def admin_story_drafts_create(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(create_draft)(req)


@app.route(route="manage/stories/drafts/{draftId}", methods=["GET"])
def admin_story_drafts_get(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(get_draft)(req)


@app.route(route="manage/stories/drafts/{draftId}", methods=["PATCH"])
def admin_story_drafts_patch(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(patch_draft)(req)


@app.route(route="manage/stories/drafts/{draftId}/messages", methods=["POST"])
def admin_story_drafts_post_message(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(post_message)(req)


@app.route(route="manage/stories/drafts/{draftId}/generate", methods=["POST"])
def admin_story_drafts_generate(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(generate_story_from_draft)(req)


@app.route(route="manage/stories", methods=["GET"])
def admin_stories_list(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(list_stories)(req)


@app.route(route="manage/stories/{storyId}", methods=["GET"])
def admin_stories_get(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(get_story)(req)


@app.route(route="manage/stories/{storyId}/publish", methods=["POST"])
def admin_stories_publish(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(publish_story)(req)


@app.route(route="manage/stories/{storyId}/unpublish", methods=["POST"])
def admin_stories_unpublish(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(unpublish_story)(req)


@app.route(route="game/start", methods=["POST"])
def game_start(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(start)(req)


@app.route(route="game/adventures", methods=["GET"])
def game_adventures_list(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(list_adventures)(req)


@app.route(route="game/adventures/{adventureId}", methods=["GET"])
def game_adventures_get(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(get_adventure)(req)


@app.route(route="manage/accounts", methods=["POST"])
def admin_accounts_add(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(add_account)(req)


@app.route(route="manage/accounts", methods=["GET"])
def admin_accounts_list(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(list_accounts)(req)


@app.route(route="manage/accounts", methods=["DELETE"])
def admin_accounts_remove(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(remove_account)(req)
