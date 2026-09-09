"""The process-wide Managed Identity credential (Constitution Principle VII).

`DefaultAzureCredential` caches tokens per scope on the *instance*, so a credential
built per request throws that cache away every time and pays a fresh IMDS round trip
for every scope it touches. A production trace of one story-creation request showed
three separate credential chains — two for Cosmos, one for Cognitive Services — each
re-walking the chain and re-fetching a token that a longer-lived instance would
already have held (#286).

Sharing one instance across the worker process is also what makes the cache useful
across *scopes*: Cosmos and Azure OpenAI tokens then live side by side in the same
credential rather than in two short-lived ones.

Safe to share: the synchronous `azure-identity` credentials are thread-safe, and the
Functions Python worker reuses its process across invocations.
"""

from __future__ import annotations

import threading
from typing import Optional

from azure.identity import DefaultAzureCredential

_credential: Optional[DefaultAzureCredential] = None
_lock = threading.Lock()


def shared_credential() -> DefaultAzureCredential:
    """The one `DefaultAzureCredential` for this worker process, built on first use."""
    global _credential
    if _credential is None:
        with _lock:
            # Re-checked under the lock: two threads can both see None above.
            if _credential is None:
                _credential = DefaultAzureCredential()
    return _credential
