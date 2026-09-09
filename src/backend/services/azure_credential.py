"""The process-wide Managed Identity credential (Constitution Principle VII).

`DefaultAzureCredential` caches tokens per scope on the instance, so one shared instance
holds the Cosmos, Graph and Azure OpenAI tokens together instead of re-acquiring each per
request. The synchronous credentials are thread-safe.
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
