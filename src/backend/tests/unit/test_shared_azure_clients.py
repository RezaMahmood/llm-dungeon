"""The clients that must outlive a single request.

Sharing is not observable from one request's behaviour, so it needs its own tests: nothing
else here would catch a client, credential or signing-key cache going back to being rebuilt
per call.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services import auth_service as auth_service_module
from backend.services import azure_credential as azure_credential_module
from backend.services import cosmos_service as cosmos_service_module
from backend.services import llm_service as llm_service_module
from backend.services.auth_service import AuthService
from backend.services.azure_credential import shared_credential
from backend.services.cosmos_service import CosmosService, shared_cosmos_service
from backend.services.llm_service import LLMService


# (module, attribute, value meaning "empty") for every process-wide cache under test.
_CACHES = (
    (azure_credential_module, "_credential", None),
    (cosmos_service_module, "_clients", {}),
    (cosmos_service_module, "_shared_service", None),
    (auth_service_module, "_jwk_clients", {}),
    (llm_service_module, "_clients", {}),
)


@pytest.fixture(autouse=True)
def _clear_process_caches():
    """These caches are deliberately process-wide, so each test needs a clean one — and
    has to hand back whatever the rest of the suite was using."""
    saved = [(module, name, getattr(module, name)) for module, name, _ in _CACHES]
    for module, name, empty in _CACHES:
        setattr(module, name, dict(empty) if isinstance(empty, dict) else empty)
    yield
    for module, name, original in saved:
        setattr(module, name, original)


# --- Managed Identity credential ---


def test_shared_credential_is_built_once_per_process():
    with patch.object(azure_credential_module, "DefaultAzureCredential") as credential_class:
        first = shared_credential()
        second = shared_credential()

    assert first is second
    credential_class.assert_called_once()


# --- Cosmos ---


def test_cosmos_services_share_one_client_per_endpoint():
    """Two services built independently — as the admin-authorization path and the request
    handler do — must land on the same client, or each re-reads the account topology."""
    with patch.object(cosmos_service_module, "CosmosClient") as client_class, patch.object(
        cosmos_service_module, "shared_credential"
    ):
        client_class.side_effect = lambda *args, **kwargs: MagicMock()
        first = CosmosService(endpoint="https://example.invalid/").client
        second = CosmosService(endpoint="https://example.invalid/").client

    assert first is second
    client_class.assert_called_once()


def test_cosmos_clients_are_not_shared_across_endpoints():
    with patch.object(cosmos_service_module, "CosmosClient") as client_class, patch.object(
        cosmos_service_module, "shared_credential"
    ):
        client_class.side_effect = lambda *args, **kwargs: MagicMock()
        first = CosmosService(endpoint="https://one.invalid/").client
        second = CosmosService(endpoint="https://two.invalid/").client

    assert first is not second
    assert client_class.call_count == 2


def test_cosmos_client_uses_the_shared_credential():
    with patch.object(cosmos_service_module, "CosmosClient") as client_class, patch.object(
        cosmos_service_module, "shared_credential"
    ) as credential:
        CosmosService(endpoint="https://example.invalid/").client

    assert client_class.call_args.kwargs["credential"] is credential.return_value


def test_an_injected_client_still_wins():
    """Test fakes are injected this way throughout the suite; sharing must not override it."""
    injected = MagicMock()

    service = CosmosService(endpoint="https://example.invalid/", client=injected)

    assert service.client is injected


def test_shared_cosmos_service_is_a_single_instance():
    assert shared_cosmos_service() is shared_cosmos_service()


# --- JWKS signing keys ---


def test_jwks_client_is_reused_across_auth_service_instances():
    """AuthService is constructed per request by the auth middleware, so the signing-key
    cache only ever elapses its TTL if it lives above the instance."""
    with patch.object(auth_service_module, "PyJWKClient") as jwk_client_class:
        first = AuthService(jwks_uri="https://example.invalid/keys")._get_jwk_client()
        second = AuthService(jwks_uri="https://example.invalid/keys")._get_jwk_client()

    assert first is second
    jwk_client_class.assert_called_once_with("https://example.invalid/keys")


def test_jwks_client_is_rebuilt_once_the_cache_window_passes():
    with patch.object(auth_service_module, "PyJWKClient") as jwk_client_class:
        jwk_client_class.side_effect = lambda uri: MagicMock()
        service = AuthService(jwks_uri="https://example.invalid/keys")
        first = service._get_jwk_client()
        # Age the cached entry past JWKS_CACHE_SECONDS rather than sleeping.
        client, created_at = auth_service_module._jwk_clients["https://example.invalid/keys"]
        auth_service_module._jwk_clients["https://example.invalid/keys"] = (
            client,
            created_at - auth_service_module.config.JWKS_CACHE_SECONDS - 1,
        )
        second = service._get_jwk_client()

    assert first is not second
    assert jwk_client_class.call_count == 2


def test_jwks_clients_are_not_shared_across_uris():
    with patch.object(auth_service_module, "PyJWKClient") as jwk_client_class:
        jwk_client_class.side_effect = lambda uri: MagicMock()
        first = AuthService(jwks_uri="https://one.invalid/keys")._get_jwk_client()
        second = AuthService(jwks_uri="https://two.invalid/keys")._get_jwk_client()

    assert first is not second


def test_an_instance_level_jwk_client_still_wins():
    """The existing auth tests set this directly to inject a fake signing key."""
    import time

    injected = MagicMock()
    service = AuthService(jwks_uri="https://example.invalid/keys")
    service._jwk_client = injected
    service._jwk_client_created_at = time.time()

    assert service._get_jwk_client() is injected


# --- Azure OpenAI ---


def test_llm_services_share_one_client_per_endpoint():
    with patch.object(llm_service_module, "OpenAIChatCompletionClient") as client_class, patch.object(
        llm_service_module, "shared_credential"
    ):
        client_class.side_effect = lambda **kwargs: MagicMock()
        first = LLMService(endpoint="https://example.invalid/").client
        second = LLMService(endpoint="https://example.invalid/").client

    assert first is second
    client_class.assert_called_once()


def test_llm_client_uses_the_shared_credential():
    with patch.object(llm_service_module, "OpenAIChatCompletionClient") as client_class, patch.object(
        llm_service_module, "shared_credential"
    ) as credential:
        LLMService(endpoint="https://example.invalid/").client

    assert client_class.call_args.kwargs["credential"] is credential.return_value


def test_llm_calls_all_run_on_one_event_loop():
    """The shared client's httpx connection pool is bound to the loop that opened it, so a
    per-call `asyncio.run()` would hand the next call a connection belonging to a closed
    loop — `RuntimeError: Event loop is closed`, intermittently."""

    async def which_loop():
        import asyncio

        return asyncio.get_running_loop()

    first = llm_service_module._run(which_loop())
    second = llm_service_module._run(which_loop())

    assert first is second
    assert not first.is_closed()


def test_llm_run_can_await_a_future_created_by_an_earlier_call():
    """The regression itself. A pending Future is genuinely bound to the loop that created
    it, and its timer only fires while that loop still runs — so awaiting it on a later
    call fails with "attached to a different loop" under a per-call `asyncio.run()` and
    succeeds only if both calls share one live loop."""
    import asyncio

    async def make_pending_future():
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        loop.call_later(0.01, lambda: future.done() or future.set_result("done"))
        return future

    async def await_future(future):
        return await future

    future = llm_service_module._run(make_pending_future())

    assert llm_service_module._run(await_future(future)) == "done"


def test_llm_run_reraises_the_original_exception_with_its_cause():
    """`_as_rate_limit_error` walks `__cause__` to find a wrapped 429, so crossing the
    thread boundary must not replace or re-wrap the exception."""
    cause = ValueError("underlying")
    wrapper = RuntimeError("wrapper")
    wrapper.__cause__ = cause

    async def boom():
        raise wrapper

    with pytest.raises(RuntimeError) as raised:
        llm_service_module._run(boom())

    assert raised.value is wrapper
    assert raised.value.__cause__ is cause


def test_concurrent_llm_calls_overlap_rather_than_serialize():
    """The daemon loop exists so calls taking seconds still run alongside each other; a
    lock around a single loop would satisfy every other test here. Two coroutines are held
    on a gate and neither is released until both have entered, so a serialized
    implementation cannot get the second one in and times out."""
    import asyncio
    import threading

    loop = llm_service_module._shared_loop()
    gate = asyncio.Event()
    entered = threading.Semaphore(0)
    results: dict[int, str] = {}

    async def held_call() -> str:
        entered.release()
        await asyncio.wait_for(gate.wait(), timeout=5)
        return "released"

    def worker(n: int) -> None:
        results[n] = llm_service_module._run(held_call())

    threads = [threading.Thread(target=worker, args=(n,), daemon=True) for n in (1, 2)]
    for thread in threads:
        thread.start()
    try:
        # Both inside the call before either can finish — the assertion that they overlap.
        assert entered.acquire(timeout=5), "second call never started; calls are serialized"
        assert entered.acquire(timeout=5), "second call never started; calls are serialized"
    finally:
        loop.call_soon_threadsafe(gate.set)
    for thread in threads:
        thread.join(timeout=5)

    assert results == {1: "released", 2: "released"}
