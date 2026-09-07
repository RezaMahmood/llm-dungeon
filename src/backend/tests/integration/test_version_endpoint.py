"""Integration tests for GET /api/version (issue #255) — the deployed backend
version surfaced by the frontend's version badge."""

from __future__ import annotations

import json

from backend.api.version import UNKNOWN_VERSION, get_version, read_version
from backend.tests.conftest import make_request


def test_returns_the_stamped_version_without_a_token(tmp_path, monkeypatch):
    # No X-Custom-Authorization header: the badge renders on the login screen,
    # so an unauthenticated caller must still get a version back.
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.4.0\n", encoding="utf-8")
    monkeypatch.setattr("backend.api.version.VERSION_FILE", version_file)

    response = get_version(make_request(url="/api/version"))

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"status": "success", "version": "1.4.0"}


def test_response_is_not_cached():
    # A cached response would pin the badge to whatever version was deployed
    # when the browser first asked — the stale-version failure the issue rules out.
    response = get_version(make_request(url="/api/version"))

    assert response.headers["Cache-Control"] == "no-store"


def test_reports_unknown_when_no_version_file_is_stamped(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.api.version.VERSION_FILE", tmp_path / "VERSION")

    response = get_version(make_request(url="/api/version"))

    assert json.loads(response.get_body())["version"] == UNKNOWN_VERSION


def test_read_version_strips_the_builds_trailing_newline(tmp_path):
    # _build-backend.yml writes the file with `echo`, so it always ends in \n.
    assert read_version(_written(tmp_path, "0.9.2\n")) == "0.9.2"


def test_read_version_treats_an_empty_file_as_unknown(tmp_path):
    assert read_version(_written(tmp_path, "   \n")) == UNKNOWN_VERSION


def _written(tmp_path, contents):
    version_file = tmp_path / "VERSION"
    version_file.write_text(contents, encoding="utf-8")
    return version_file
