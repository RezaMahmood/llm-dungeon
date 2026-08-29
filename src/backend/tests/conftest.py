"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import azure.functions as func
import pytest


def make_request(method: str = "GET", url: str = "/api/test", token: str | None = None, body: bytes = b"") -> func.HttpRequest:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return func.HttpRequest(method=method, url=url, headers=headers, params={}, body=body)


@pytest.fixture
def request_factory():
    return make_request
