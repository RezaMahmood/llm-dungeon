"""Azure Functions app entry point — registers HTTP routes for auth, admin, and game APIs."""

import azure.functions as func

from backend.api.admin.stories import create_story, list_stories
from backend.api.auth.login import login
from backend.api.auth.logout import logout
from backend.api.auth.me import me
from backend.api.game.start import start
from backend.api.utils import server_error

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _guarded(handler):
    def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        try:
            return handler(req)
        except Exception:  # noqa: BLE001 - convert unexpected errors to a generic 500
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
