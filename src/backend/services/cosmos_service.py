"""Cosmos DB connection and query helpers, authenticated via Managed Identity."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Iterable, Optional

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from backend.config import config
from backend.services.azure_credential import shared_credential

logger = logging.getLogger("cosmos_service")

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 0.5

# One CosmosClient per endpoint per worker process: a client caches database-account
# discovery and container properties on itself, and re-fetches both when rebuilt.
_clients: dict[str, CosmosClient] = {}
_clients_lock = threading.Lock()


def _shared_client(endpoint: str) -> CosmosClient:
    with _clients_lock:
        client = _clients.get(endpoint)
        if client is None:
            client = CosmosClient(endpoint, credential=shared_credential())
            _clients[endpoint] = client
        return client


class CosmosService:
    """Thin wrapper around the Cosmos DB SDK with retry logic for transient failures.

    Authentication uses Managed Identity (DefaultAzureCredential) per Constitution
    Principle VII — no shared keys or connection strings.
    """

    def __init__(self, endpoint: Optional[str] = None, client: Optional[CosmosClient] = None) -> None:
        self._endpoint = endpoint or config.COSMOS_ENDPOINT
        self._client = client
        self._database = None

    @property
    def client(self) -> CosmosClient:
        if self._client is None:
            self._client = _shared_client(self._endpoint)
        return self._client

    @property
    def database(self):
        if self._database is None:
            self._database = self.client.get_database_client(config.COSMOS_DATABASE_NAME)
        return self._database

    def get_container(self, name: str):
        return self.database.get_container_client(name)

    def query(
        self,
        container_name: str,
        sql: str,
        params: Optional[list[dict[str, Any]]] = None,
        partition_key: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Execute a parameterized query on a container, with retry on transient failures."""
        container = self.get_container(container_name)
        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                items: Iterable[dict[str, Any]] = container.query_items(
                    query=sql,
                    parameters=params or [],
                    partition_key=partition_key,
                    enable_cross_partition_query=partition_key is None,
                )
                return list(items)
            except CosmosHttpResponseError as exc:
                last_error = exc
                if exc.status_code and exc.status_code < 500:
                    logger.error("Cosmos query failed (non-transient): %s", exc)
                    raise
                logger.warning("Transient Cosmos error on attempt %d/%d: %s", attempt, _MAX_RETRIES, exc)
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
        logger.error("Cosmos query failed after %d attempts: %s", _MAX_RETRIES, last_error)
        raise last_error  # type: ignore[misc]


# What callers fall back to when no service is injected, so the database and container
# proxies are reused across requests along with the client.
_shared_service: Optional[CosmosService] = None
_shared_service_lock = threading.Lock()


def shared_cosmos_service() -> "CosmosService":
    global _shared_service
    if _shared_service is None:
        with _shared_service_lock:
            if _shared_service is None:
                _shared_service = CosmosService()
    return _shared_service
