"""Azure Functions app entry point — registers HTTP routes for auth, admin, and game APIs."""

import logging

import azure.functions as func

from backend.api.admin.accounts import add_account, list_accounts
from backend.api.admin.stories import create_story, list_stories
from backend.api.auth.login import login
from backend.api.auth.logout import logout
from backend.api.auth.me import me
from backend.api.game.start import start
from backend.api.utils import server_error
from backend.config import config
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("function_app")

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


@app.route(route="admin/stories/create", methods=["POST"])
def admin_stories_create(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(create_story)(req)


@app.route(route="admin/stories", methods=["GET"])
def admin_stories_list(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(list_stories)(req)


@app.route(route="game/start", methods=["POST"])
def game_start(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(start)(req)


@app.route(route="admin/accounts", methods=["POST"])
def admin_accounts_add(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(add_account)(req)


@app.route(route="admin/accounts", methods=["GET"])
def admin_accounts_list(req: func.HttpRequest) -> func.HttpResponse:
    return _guarded(list_accounts)(req)
