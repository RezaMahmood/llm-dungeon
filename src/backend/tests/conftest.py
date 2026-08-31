"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import azure.functions as func
import pytest


def make_request(
    method: str = "GET",
    url: str = "/api/test",
    token: str | None = None,
    body: bytes = b"",
    route_params: dict | None = None,
    headers: dict | None = None,
) -> func.HttpRequest:
    all_headers = dict(headers or {})
    if token is not None:
        all_headers["Authorization"] = f"Bearer {token}"
    return func.HttpRequest(method=method, url=url, headers=all_headers, params={}, route_params=route_params or {}, body=body)


@pytest.fixture
def request_factory():
    return make_request
