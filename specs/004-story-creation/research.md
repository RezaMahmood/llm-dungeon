# Research: Story Creation

**Date**: 2026-08-29 | **Status**: Research Phase Complete (redesign amendments 2026-08-31)

**Amendment (2026-08-31)**: Following the T033 acceptance walkthrough (2026-08-30) and the
resulting spec.md Clarifications, this feature's design changed from auto-generate-on-
completeness to explicit Save/Abandon/Finished with a purely frontend, local-storage draft
and a blob-stored cover image. §1, §2, and §4 below still apply to the one LLM call this
feature keeps (Tab 02's one-shot outline suggestion); §3's Cosmos-TTL-draft design and the
conversational multi-turn exchange described in §4/§5 are superseded — see §6 and §7.

## 1. Calling the Azure AI Foundry Deployed Model

**Unknown**: `007-azure-infrastructure-provisioning` (FR-015) provisions "an Azure AI Foundry resource with at least one deployed language model," reachable only via Managed Identity over a private endpoint (FR-007/FR-008). No spec so far has actually called it — `004-story-creation` is the first feature that needs a real LLM client, so the SDK and auth pattern need to be chosen here.

**Decision**: `azure-ai-inference` (the Azure AI Foundry model-catalog SDK), authenticated via `azure-identity`'s `DefaultAzureCredential` (already a project dependency, already used by `CosmosService` per Constitution Principle VII). A new `src/backend/services/llm_service.py` wraps `azure.ai.inference.ChatCompletionsClient`, constructed once per invocation the same way `CosmosService` lazily builds its client.

**Rationale**: `azure-ai-inference` is Microsoft's unified client for models deployed through Azure AI Foundry's model catalog (not tied to a single model vendor), and supports Entra ID/Managed Identity authentication for AAD-secured Foundry endpoints — matching FR-008's "no API keys" requirement without needing to know in advance which model family `007` deploys.

**Alternatives considered**:
- `openai` Python SDK pointed at an Azure OpenAI-compatible endpoint (`azure_ad_token_provider`): only works cleanly if `007` deploys an OpenAI-family model specifically; `azure-ai-inference` is the more general choice for "at least one deployed language model" from the Foundry catalog.
- Raw HTTPS calls with a hand-rolled bearer token: reinvents what `azure-ai-inference` already provides (retries, typed request/response models); rejected as unnecessary complexity.

**Validation**: `llm_service.py` is unit-tested against a mocked `ChatCompletionsClient` (no live Foundry call in tests, matching how `cosmos_service.py`'s tests mock `CosmosClient`).

**Amendment (2026-08-30)**: `azure-ai-inference` was retired by Microsoft on 2026-08-26, and the endpoint/auth pairing above never actually worked against `007`'s provisioned resource (a plain `azurerm_cognitive_account` of `kind = "OpenAI"`, which only serves the classic `/openai/deployments/{name}/chat/completions` route — not the `{endpoint}/chat/completions` route `azure-ai-inference`'s `ChatCompletionsClient` calls). `llm_service.py` now uses `agent_framework.openai.OpenAIChatCompletionClient` (the `agent-framework-openai` package) instead: same Managed-Identity auth (`credential=DefaultAzureCredential()`, Principle VII), same JSON-mode call shape, but talking the endpoint/API-version pairing Azure OpenAI actually expects, with structured output validated via Pydantic `response_format` models rather than manual `json.loads`. Only the plain chat-completion client is used — no agent/tool/workflow orchestration from the framework (YAGNI) — so this stays a drop-in replacement for the retired SDK, not a framework adoption. `007`'s Terraform gained a matching `AZURE_AI_FOUNDRY_DEPLOYMENT_NAME` app setting (the deployment name Azure OpenAI addresses by, distinct from the bare endpoint).

---

## 2. LLM Observability (Constitution Principle VI, NON-NEGOTIABLE)

**Unknown**: The constitution requires every LLM call to record full prompt, full response, input/output token counts, per-call cost, and latency, queryable in Application Insights and attributable to a request/session — but no prior feature has implemented any OpenTelemetry instrumentation yet. This is genuinely new infrastructure, not a pattern to copy from an existing file.

**Decision**: Add `azure-monitor-opentelemetry` (Microsoft's single-call distro: `configure_azure_monitor()`) to `src/backend/requirements.txt`, initialized once in `function_app.py`. `llm_service.py` wraps every Foundry call in a span (`gen_ai.story_creation.exchange` / `gen_ai.story_creation.generate`) and sets span attributes for the full prompt text, full response text, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, a computed `gen_ai.cost_usd`, and `gen_ai.latency_ms`; the span is parented under the incoming HTTP request span so it is already attributable to that admin's draft/session without extra plumbing.

**Rationale**: `configure_azure_monitor()` is the Microsoft-documented minimum-code path from OpenTelemetry to Application Insights and needs no manual exporter wiring; naming attributes under the `gen_ai.*` prefix follows the OpenTelemetry GenAI semantic conventions, so future features (`008-core-gameplay`'s narration calls, `011-story-import`) can adopt the same span shape instead of inventing a new one per feature.

**Cost computation**: `gen_ai.cost_usd = input_tokens * PRICE_PER_INPUT_TOKEN + output_tokens * PRICE_PER_OUTPUT_TOKEN`, with the two price constants read from Function App configuration (`LLM_INPUT_TOKEN_PRICE_USD` / `LLM_OUTPUT_TOKEN_PRICE_USD`) rather than hard-coded, since the exact deployed model (and its price) is a `007` decision outside this spec's control.

**Alternatives considered**:
- Structured logging only (no OTel spans): rejected — the constitution specifically names OpenTelemetry as the instrumentation layer (not "logging"), and Application Insights' trace/log query experience is weaker for this than span attributes.
- Deferring telemetry to a later feature: rejected — Principle VI is NON-NEGOTIABLE and applies to "every LLM interaction"; `004` is the first to make one, so it cannot ship without it.

**Validation**: A unit test asserts `llm_service.py` calls `tracer.start_as_current_span` with the expected attribute keys populated from a mocked Foundry response's `usage` block.

---

## 3. Session/Draft State and the "No Persistence on Abandonment" Rule (FR-005)

**Unknown**: The wizard's four steps are reachable in any order (per the constitution's screen contract) and the guiding-question conversation happens across multiple HTTP calls to stateless Azure Functions — so something has to hold the in-progress answers between calls. FR-005 requires that an abandoned session leave nothing persisted, and the Assumptions explicitly rule out resuming an abandoned session.

**Decision**: A new Cosmos container, `storyDrafts`, holds one document per in-progress creation session (`entityType: "StoryDraft"`), partitioned by `/id` (the draft id), with a Cosmos **TTL** set on each write (24 hours since last update). The draft document is deleted the moment it successfully becomes a persisted `Story` (see data-model.md); if the administrator abandons the session, the TTL expires it automatically with no cleanup code.

**Rationale**: Cosmos's native per-item TTL turns FR-005 into a storage-level guarantee instead of application logic that could be forgotten or buggy — an abandoned draft simply ceases to exist, and it was never a `Story` document, so `005-story-publishing`/`006-adventure-and-character-setup` never see it regardless of TTL timing. This also directly satisfies the Assumption that resuming an abandoned session isn't required: a draft is only resumable while its TTL hasn't lapsed, and nothing promises longer.

**Alternatives considered**:
- Frontend-only state (no backend draft document): would satisfy FR-005 trivially but breaks the constitution's "reachable in any order" + refresh-safe wizard expectation, and can't hold multi-turn LLM conversation history across a page reload.
- Explicit "abandon" endpoint with a delete: adds a state transition FR-005 doesn't require the admin to trigger (they can just... stop), and still leaves orphaned drafts from closed tabs/crashed sessions without TTL as a backstop anyway. TTL is added regardless, making the explicit endpoint redundant (YAGNI).

**Validation**: Integration test creates a draft, asserts it is queryable, then asserts (via a short TTL override in test configuration) that it is gone after expiry and was never visible via `GET /api/manage/stories`.

---

## 4. Turning Free-Text Answers into Structured Fields

**Unknown**: FR-001 requires plain-language input; FR-008 requires character types and completion criteria to land in dedicated structured fields, not raw prose. Something has to reliably convert the conversational side of the wizard into that structure.

**Decision**: Every Foundry call in the guiding-question exchange (`llm_service.generate_exchange_response`) uses the model's JSON response-format mode, with a fixed response schema: `{ "assistantMessage": string, "fieldUpdates": { ...partial Draft fields } }`. The backend merges `fieldUpdates` into the draft document; it never asks the LLM to freely author the actual Cosmos write.

**Rationale**: Constraining the model's output to a known JSON shape (widely supported as a model/deployment feature in the Foundry catalog) avoids building a separate NLU/parsing layer, and keeps the failure mode simple: if the model's JSON doesn't validate against the expected shape, the backend treats it the same as the edge case already in the spec ("LLM's generated configuration is incomplete or malformed... system does not persist... surfaces the problem"), returning an error for that turn without corrupting the draft.

**Alternatives considered**:
- Regex/keyword extraction over free text: unreliable for open-ended natural language (the entire premise of FR-001); rejected.
- A second, smaller NLU model dedicated to extraction: adds a second Foundry deployment and cost path `007` doesn't provision; rejected as unnecessary complexity (Principle IV).

**Validation**: Unit tests feed `llm_service` a mocked Foundry response with valid and invalid JSON payloads and assert the merge succeeds / the turn is rejected without a partial write, respectively.

---

## 5. Placement of the New Character-Types/Completion-Criteria Fields (FR-008)

**Unknown**: The clarified spec requires dedicated fields for character types and completion criteria, but the design mockup (`specs/designs/04-admin-wizard.html`) only renders one step's panel (step 02, "World & setting") and has no field for either — the mockup predates this clarification.

**Decision**: Place both as new sub-sections within the existing "World & setting" step's panel (alongside the world prompt / rules fields already there), each a simple repeatable-row list (add/remove), styled with the existing design-token form primitives (`.field`, `.input`, `.btn-secondary` for "Add"). This is an implementation-level layout choice, not a new screen contract.

**Rationale**: "World & setting" is already the step most semantically connected to what a character type or a win/lose condition is about, and it is the one step the reference mockup actually shows field styling for, so extending it keeps the new fields visually consistent without inventing a fifth step or reopening the screen-contract decision made during clarification.

**Alternatives considered**: A dedicated fifth wizard step for characters/criteria — rejected for now as a bigger design change than this spec's clarification called for ("added to the existing steps **or** an additional step" left both open); revisit only if the World & Setting panel becomes visually crowded during implementation.

---

## 6. Cover Image Storage (resolves the T033-flagged "coverImageUrl has no defined meaning" question)

**Unknown**: The original data-model.md left `coverImageUrl`'s expected content unspecified — an external link, an uploaded/managed asset reference, or something else.

**Decision**: The Session 2026-08-30 Clarifications (FR-009) settle this: the cover image is a file uploaded from the administrator's own device, written to blob storage on Save, with the `Story` record storing a reference (the blob's URL) rather than an externally-hosted link or the image bytes themselves.

**Infrastructure**: No new infrastructure is needed. `007-azure-infrastructure-provisioning` already provisions a Storage Account + `assets` blob container for "application-generated or static assets" (`specs/007-azure-infrastructure-provisioning/data-model.md`), reachable from Azure Functions via Managed Identity (`Storage Blob Data Contributor`) over a private endpoint — the same zero-trust pattern `CosmosService` already uses (Constitution Principle VII). This feature is simply the first backend code path to use that existing resource (`blob_service.py`), writing objects under a `story-covers/{storyId}/` prefix inside the shared `assets` container so a dedicated container isn't required. `STORAGE_ACCOUNT_URL` and `STORY_COVER_IMAGES_CONTAINER` (defaulting to `assets`) are added to `src/backend/config.py`/`.env.example`, mirroring `007`'s already-documented `STORAGE_ACCOUNT_URL`/`STORAGE_CONTAINER` deployment configuration.

**Rationale**: Reusing the already-provisioned assets container avoids adding new Terraform resources (or a `007` scope change) for a need `007` already anticipated generically; a `story-covers/` prefix keeps cover images logically separated without a second container, role assignment, or private endpoint to provision and audit.

**Validation**: `test_blob_service.py` mocks `BlobServiceClient` (no live Azure Storage call, matching `cosmos_service.py`'s tests); the integration test for `POST /manage/stories/{storyId}/cover-image` asserts the returned `Story.coverImageUrl` is the blob client's URL.

---

## 7. Explicit Save/Abandon/Finished Replaces Auto-Generation-on-Completeness (resolves the T033-flagged premature-generation bug)

**Unknown**: FR-004 originally required the system to generate and auto-persist a `Story` the moment a `StoryDraft` became "complete" (world prompt + ≥1 character type + ≥1 completion criterion), with completeness defined independently of whether the administrator had ever visited Tabs 03/04. The T033 walkthrough showed this could — and did — jump the administrator straight from a single conversational exchange to a finished, generated-story screen, mid-flow and without warning.

**Decision**: The Session 2026-08-30 Clarifications replace this entirely. There is no more automatic generation trigger and no more server-side `StoryDraft`/Cosmos-TTL resource (§3, above, is superseded). Instead:
- A `Story` is written to Cosmos only on an explicit **Save** (FR-004), available from any tab at any time, gating on nothing but a non-empty `name` for the very first Save.
- In-progress, unsaved field values across all four tabs live in the browser's local storage (FR-010) — a purely frontend concern; nothing analogous to the old draft document is sent to or held by the backend before a Save.
- **Abandon** (FR-013/014) and **Finished** (FR-015) are explicit, confirmed actions the administrator takes to end a session, rather than an implicit TTL expiry or an auto-generation side effect.

**Rationale**: Removing the "complete → auto-generate → auto-persist" step removes the exact failure mode T033 found — there is no code path left that can silently replace the wizard view mid-conversation. Moving the draft to local storage also removes an entire class of infrastructure (a TTL-enabled Cosmos container, its cleanup semantics, and the server-side merge/completeness logic) that existed largely to support a design this redesign no longer needs (YAGNI, Constitution Principle IV) — the browser is a perfectly adequate store for data that is explicitly defined as non-authoritative until Save.

**Alternatives considered**:
- Keep auto-generation but require all four tabs to be visited first: considered directly in the T033 walkthrough notes; rejected once the Clarifications session determined explicit Save was the more predictable and simpler model to reason about (and matches how every other admin surface in this codebase — accounts, `005-story-publishing` — already works: an explicit action commits a change).
- Keep the server-side `StoryDraft`/TTL container but gate generation behind a manual trigger: would still require maintaining the draft container, its TTL semantics, and a merge step whose only remaining purpose (multi-turn conversational fill-in) is also removed by FR-003's one-shot Suggest redesign — strictly more moving parts for no remaining benefit.

**Validation**: `src/backend/tests/unit/test_story_service.py` and `src/backend/tests/integration/test_admin_stories_endpoint.py` cover create/update/delete/cover-image directly against `Story`, with no draft entity involved; `src/frontend/tests/integration/admin_story_wizard_flow.test.jsx` covers the local-storage draft surviving tab switches and reloads, Save's create-then-update semantics, and confirmed Abandon/Finished.
