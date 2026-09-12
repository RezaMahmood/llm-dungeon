# Contract: Scripted LLM Endpoint

**Consumers**: backend tests (US3), the local stack (US4 — turn taking).
**Implementation**: `src/backend/tests/harness/llm_stub.py`.

Speaks enough of the OpenAI chat-completions wire format for the **real**
`OpenAIChatCompletionClient` to talk to it. The point is that `llm_service.py`'s retry,
error mapping, parsing and cost computation all execute; nothing in `llm_service` is
patched.

## Selecting a scenario

The client is constructed by the application, not the test, so the scenario cannot be a
constructor argument. It is selected **per stub instance** — each test starts a stub
pre-programmed with the behaviour it wants and points `LLMService(endpoint=…)` at it:

```python
with llm_stub(Scenario.RATE_LIMIT_THEN_OK, failures=2) as stub:
    service = LLMService(endpoint=stub.endpoint, credential=FakeCredential())
```

A single stub may also be re-programmed mid-test (`stub.set(...)`) for sequences a single
scenario does not express.

## `POST /openai/deployments/{deployment}/chat/completions` *(and the `/v1/` form)*

Both route shapes are accepted so the stub works regardless of which the Azure-flavoured
client constructs.

### `ok`

```json
{
  "id": "chatcmpl-local", "object": "chat.completion", "created": 0,
  "model": "<deployment>",
  "choices": [{"index": 0, "finish_reason": "stop",
               "message": {"role": "assistant", "content": "<body>"}}],
  "usage": {"prompt_tokens": <input_tokens>,
            "completion_tokens": <output_tokens>,
            "total_tokens": <sum>}
}
```

`usage` is echoed from what the test set, so the assertion on `gen_ai.usage.input_tokens`,
`gen_ai.usage.output_tokens` and `gen_ai.cost_usd` compares against a number the test chose
and a price the config declares — not against a value the stub invented (US3-5).

### `rate_limit_then_ok` / `rate_limit_always`

`429` with an OpenAI-shaped error body and a `Retry-After` header:

```
HTTP/1.1 429 Too Many Requests
Retry-After: <retry_after>

{"error": {"code": "429", "message": "Requests to the ... have exceeded token rate limit"}}
```

`rate_limit_then_ok` returns `429` exactly `failures` times, then `ok`. The stub **counts
the attempts it saw**, and the test asserts on that count — this is how "it retried" is
verified as observed behaviour rather than inferred from an eventual success.

`Retry-After` is set deliberately so `_retry_after_seconds` parses a header rather than
falling back. Keep the value small (sub-second) so the backoff path is exercised without
the test sleeping meaningfully.

### `content_filter`

`400` with the Azure content-filter error shape, which is what
`_as_content_filter_error` pattern-matches to raise `LLMContentFilteredError`:

```json
{"error": {"code": "content_filter", "status": 400,
           "message": "The response was filtered due to the prompt triggering ...",
           "innererror": {"code": "ResponsibleAIPolicyViolation",
                          "content_filter_result": {"violence": {"filtered": true, "severity": "medium"}}}}}
```

The test asserts both the raised `LLMContentFilteredError` **and** the player's
content-safety standing update (US3-3) — the mapping alone is only half the behaviour.

### `malformed_json` / `missing_key`

`200` with a well-formed envelope whose `message.content` is, respectively, text that is
not JSON at all, and JSON missing a key the parser requires. Both must surface as
`LLMOutputError` (US3-4). These are distinct cases because they fail at different points in
the parse and have historically been handled by different branches.

## Invariants

1. **No production module is patched.** If a test needs `unittest.mock` against anything in
   `llm_service`, that test belongs in the existing object-level tier, not this one.
2. **Deterministic.** Same scenario, same request → byte-identical response. No sampling,
   no clock, no randomness. This is what makes the stub serviceable for US4's hand-play and
   visual work as well as for assertions.
3. **Loopback only**, ephemeral port, shut down by the context manager even on failure.
4. **Attempt counting is part of the contract** — `stub.attempts` is the retry evidence.
