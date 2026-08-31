"""BlobService — uploads a Story's cover image to blob storage (FR-009).

The blob storage account and its `assets` container already exist, provisioned by
`007-azure-infrastructure-provisioning` for "application-generated or static assets"
(see `specs/007-azure-infrastructure-provisioning/data-model.md`); this feature does not
provision new infrastructure, it just becomes the first backend code path to use it.
Authentication is Managed Identity (`DefaultAzureCredential`), matching `CosmosService`'s
existing pattern (Constitution Principle VII)."""

from __future__ import annotations

from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from backend.config import config


class BlobService:
    def __init__(
        self,
        account_url: Optional[str] = None,
        container_name: Optional[str] = None,
        client: Optional[BlobServiceClient] = None,
    ) -> None:
        self._account_url = account_url or config.STORAGE_ACCOUNT_URL
        self._container_name = container_name or config.STORY_COVER_IMAGES_CONTAINER
        self._client = client

    @property
    def client(self) -> BlobServiceClient:
        if self._client is None:
            self._client = BlobServiceClient(account_url=self._account_url, credential=DefaultAzureCredential())
        return self._client

    def upload_cover_image(self, story_id: str, filename: str, content: bytes, content_type: Optional[str]) -> str:
        """Uploads `content` under `story-covers/{story_id}/{filename}` in the shared
        assets container, overwriting any prior cover for this story, and returns the
        blob's URL — the reference the Story record stores (data-model.md)."""
        blob_name = f"story-covers/{story_id}/{filename}"
        container_client = self.client.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type or "application/octet-stream"),
        )
        return blob_client.url
