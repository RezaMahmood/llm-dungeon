"""Unit tests for BlobService.upload_cover_image (FR-009) — the BlobServiceClient is
mocked, no live Azure Storage call (matching cosmos_service.py's tests mocking
CosmosClient)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.blob_service import BlobService


def test_upload_cover_image_uploads_under_story_covers_prefix_and_returns_url():
    client = MagicMock()
    container_client = MagicMock()
    blob_client = MagicMock()
    blob_client.url = "https://example.blob.core.windows.net/assets/story-covers/story-1/cover.png"
    client.get_container_client.return_value = container_client
    container_client.get_blob_client.return_value = blob_client

    service = BlobService(container_name="assets", client=client)
    url = service.upload_cover_image("story-1", "cover.png", b"fake-bytes", "image/png")

    client.get_container_client.assert_called_once_with("assets")
    container_client.get_blob_client.assert_called_once_with("story-covers/story-1/cover.png")
    blob_client.upload_blob.assert_called_once()
    args, kwargs = blob_client.upload_blob.call_args
    assert args[0] == b"fake-bytes"
    assert kwargs["overwrite"] is True
    assert kwargs["content_settings"].content_type == "image/png"
    assert url == blob_client.url


def test_upload_cover_image_defaults_content_type_when_missing():
    client = MagicMock()
    blob_client = MagicMock()
    client.get_container_client.return_value.get_blob_client.return_value = blob_client

    service = BlobService(container_name="assets", client=client)
    service.upload_cover_image("story-1", "cover.png", b"fake-bytes", None)

    _, kwargs = blob_client.upload_blob.call_args
    assert kwargs["content_settings"].content_type == "application/octet-stream"
