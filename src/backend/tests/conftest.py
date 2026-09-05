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
) -> func.HttpRequest:
    headers = {}
    if token is not None:
        headers["X-MSAL-Authorization"] = f"Bearer {token}"
    return func.HttpRequest(method=method, url=url, headers=headers, params={}, route_params=route_params or {}, body=body)


@pytest.fixture
def request_factory():
    return make_request
