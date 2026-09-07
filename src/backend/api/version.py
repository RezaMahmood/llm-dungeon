"""Deployed-version endpoint (issue #255).

Deliberately anonymous: the version badge renders on every page, including the
login screen, so this must answer before any token exists. A build version is
not sensitive, and no account or story data is reachable from here.
"""

from __future__ import annotations

import logging
from pathlib import Path

import azure.functions as func

from backend.api.utils import json_response

logger = logging.getLogger("api.version")

# _build-backend.yml stamps the semantic-release version into `src/VERSION`
# before zipping `src/` as the deploy root, so at runtime the file sits beside
# function_app.py — one level above the `backend` package.
VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"

# What the badge shows when no stamped version is present: a local `func start`,
# or a deploy whose artifact predates this stamping step. Never a hardcoded
# number, which would silently go stale and misreport what is deployed.
UNKNOWN_VERSION = "unknown"


def read_version(version_file: Path | None = None) -> str:
    """The deployed backend version, or UNKNOWN_VERSION when it can't be read.

    Read per request rather than cached at import: the file is a few bytes, and
    a stale cache in a warm worker is exactly the "no manual/stale hardcoding"
    failure the issue asks to avoid.
    """
    path = VERSION_FILE if version_file is None else version_file
    try:
        # The build writes this with `echo`, so it carries a trailing newline.
        version = path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.info("No stamped VERSION file at %s — reporting %s", path, UNKNOWN_VERSION)
        return UNKNOWN_VERSION
    return version or UNKNOWN_VERSION


def get_version(req: func.HttpRequest) -> func.HttpResponse:
    return json_response({"status": "success", "version": read_version()}, status_code=200)
