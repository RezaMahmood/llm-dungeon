"""Azure Functions app entry point — registers HTTP routes for auth, admin, and game APIs."""

import logging
from urllib.parse import urlparse

import azure.functions as func
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, Status, StatusCode

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
from backend.observability.setup import setup_observability
from backend.services.account_provisioning_service import AccountProvisioningService

logger = logging.getLogger("function_app")
tracer = trace.get_tracer("backend.function_app")

# Principle VI (Observability & AI Cost Transparency, NON-NEGOTIABLE) — one-call
# OpenTelemetry -> Application Insights wiring, initialized once at startup so
# every later span (e.g. llm_service.py's gen_ai.* spans) is exported.
setup_observability()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

if config.SEED_ADMIN_EMAIL:
    AccountProvisioningService().ensure_seed_administrator(config.SEED_ADMIN_EMAIL)


def _guarded(handler):
    def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        # Every route's request span is created here, rather than relied on from
        # auto-instrumentation, so FR-001/FR-002's span/exception guarantees hold
        # the same way whether the request arrives through the real Azure
        # Functions host or a test calls this wrapper directly (FR-002, contract §1).
        # Extracting the incoming W3C `traceparent` (the frontend's Application
        # Insights JS SDK sends one on every dependency call) parents this span
        # under the caller's trace instead of starting a new, uncorrelated one —
        # this is what FR-005/contract §4's frontend<->backend correlation
        # actually depends on. HTTP header names are case-insensitive, and the
        # propagator's getter looks up the lowercase "traceparent" key exactly —
        # lowercasing explicitly here means correlation doesn't depend on
        # whichever casing a proxy or client happened to send it in.
        incoming_context = extract({key.lower(): value for key, value in req.headers.items()})
        # req.url is the full incoming URL (scheme/host and, for a real Azure
        # Functions request, potentially a querystring) — using it unparsed
        # would make http.route unstable/high-cardinality and could leak
        # querystring content into telemetry. Only the path is a route-shaped,
        # queryable identifier.
        path = urlparse(req.url).path
        # req.route_params gives each dynamic segment's *resolved* value (e.g.
        # {"storyId": "abc123"}) — substituting the placeholder name back in
        # keeps http.route a low-cardinality route template (matching OTel's
        # semantic-convention expectation) rather than one unique string per
        # concrete resource ID.
        route = path
        for name, value in (req.route_params or {}).items():
            route = route.replace(f"/{value}", f"/{{{name}}}")
        with tracer.start_as_current_span(
            f"{req.method} {route}",
            context=incoming_context,
            kind=SpanKind.SERVER,
            attributes={"http.method": req.method, "http.route": route},
        ) as span:
            try:
                response = handler(req)
                span.set_attribute("http.status_code", response.status_code)
                return response
            except Exception as exc:  # noqa: BLE001 - convert unexpected errors to a generic 500
                logger.exception("Unhandled error in %s", handler.__name__)
                # No description here (e.g. str(exc)) — record_exception below
                # already captures the exception's message/stacktrace in the
                # canonical exception event; a second, less-audited copy on the
                # span status isn't needed and is one more place a sensitive
                # exception message could end up (FR-006/Principle X).
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                response = server_error()
                span.set_attribute("http.status_code", response.status_code)
                return response

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
