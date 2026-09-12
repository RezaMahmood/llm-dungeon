# Contract: Local Token Issuer

**Consumers**: backend tests (US1), the local stack's SPA and API (US4).
**Implementation**: `src/backend/tests/harness/identity.py` — a module the deployed
package does not contain and `function_app.py` never imports (FR-004).

## HTTP surface

Served by a stdlib `http.server` thread bound to `127.0.0.1` on an ephemeral port.

### `GET /keys`

The JWKS document. This is the URI handed to `AuthService(jwks_uri=…)`, and it is what
makes `PyJWKClient` do real key resolution instead of being patched out.

```json
{
  "keys": [
    {
      "kty": "RSA", "use": "sig", "alg": "RS256",
      "kid": "<per-session key id>",
      "n": "<base64url modulus>", "e": "AQAB"
    }
  ]
}
```

- `200` with exactly the currently-published key(s).
- After `rotate()`, the previous key is **absent** — this is what makes a token signed by
  the old key fail with an unknown-`kid` error rather than a bad-signature error, which is
  the real-world failure shape (US1 scenario 2).

### `GET /.well-known/openid-configuration` *(optional, US4 only)*

Discovery document with `issuer` and `jwks_uri`, for the SPA's MSAL configuration if the
local stack needs it. Backend tests do not use it — `AuthService` takes `jwks_uri` directly.

## Python surface

```python
issuer = LocalTokenIssuer()                  # generates a keypair, starts the server
issuer.jwks_uri                              # -> "http://127.0.0.1:<port>/keys"
issuer.issuer_for(tid)                       # -> "https://login.microsoftonline.com/{tid}/v2.0"
issuer.mint(identity, *, audience=None, issuer=None, expires_in=3600, key=None) -> str
issuer.rotate() -> None                      # new keypair AND new jwks_uri (see below)
issuer.close() -> None
```

### Invariants

1. **Validation is never weakened.** Every token this issuer mints is a genuine RS256 JWT
   verified by the unmodified `AuthService.validate_token`. There is no code path in which
   signature, `exp`, `iss` or `aud` checking is skipped, softened, or short-circuited
   (FR-005).
2. **`rotate()` must also change `jwks_uri`.** `auth_service._shared_jwk_client` caches
   `PyJWKClient` instances process-wide, keyed by URI, for `JWKS_CACHE_SECONDS` (24 hours).
   Rotating the keypair behind the same URI would be invisible to a warm cache, and the
   rotation test would pass or fail depending on what ran before it. Rotation therefore
   binds a new path or port.
3. **Loopback only.** The server binds `127.0.0.1`, never `0.0.0.0` — it must not be
   reachable from outside the machine even momentarily.
4. **Ephemeral keys.** The private key exists only in memory for the life of the process.
   It is never written to disk and never committed. There is no fixture key file.
5. **`.invalid` addresses only** (FR-003) — asserted when the identity is constructed.

### Default claims

`sub`, `oid`, `tid`, `preferred_username`, `name`, `roles`, `iss`, `aud`, `iat`, `nbf`,
`exp` — matching the shape of a real Entra v2.0 access token, so that code reading a claim
finds it where production puts it.

## Error behaviour tests rely on

| Minting call | `validate_token` result |
|---|---|
| default | valid |
| `key=<foreign key>` | invalid — signing key not found |
| `expires_in=-60` | invalid — expired |
| `issuer="https://evil.example/v2.0"` | invalid — issuer mismatch |
| `audience="urn:something-else"` | invalid — audience mismatch |
| `audience=config.AZURE_APP_ID` | **valid** (US1-4) |
| `audience=f"api://{config.AZURE_APP_ID}"` | **valid** (US1-4, the #212 form) |
| `issuer=issuer_for(MICROSOFT_CONSUMERS_TENANT_ID)` | **valid** (US1-3) |
