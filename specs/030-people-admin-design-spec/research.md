# Research: People (Admin) Screen Design-Spec Conformance

## Decision 1: Do not add a Name field

**Decision**: The table keeps a single identity column (the Microsoft account email); no
display-name field is added to `ProvisionedAccountEntry` or the UI.

**Rationale**: `ProvisionedAccountEntry` (`003-account-provisioning-done`) has never carried a
name — accounts are added and identified purely by their Microsoft (Entra) email. Inventing a
name (e.g. deriving one from the email's local part, or introducing a free-text field an
administrator fills in) would either fabricate an identity claim the system cannot verify, or
require a genuinely new capability (self-reported name at first sign-in, an admin-entered
field, or a directory read) that changes the account model and its validation — out of
proportion to a design-conformance feature and better decided on its own.

**Alternatives considered**:
- *Derive a display label from the email local-part* (e.g. `ada.bell@school.internal` →
  "Ada Bell") — rejected: this is a guess dressed up as data; an email local-part is not
  guaranteed to encode a real name, and presenting it as one misleads an administrator.
- *Add a free-text "name" field to the add-account form* — rejected as new scope: it changes
  `ProvisionedAccountEntry`'s schema and `add_or_merge`'s validation, needs its own
  functional requirements (is it required? editable later? shown to the player?), and the
  issue's own attached spec treats it as already-solved data, not something this feature is
  asked to design.

## Decision 2: Two Status states, not three

**Decision**: Render "Signed in" (bound) and "Never signed in" (not bound) only. The design's
"Signed out · {relative time}" state is not implemented.

**Rationale**: `AccountProvisioningService.authorize_sign_in` sets `dateBound` exactly once,
on the *first* successful bind — every later sign-in reuses the same bound `objectId` and
never updates `dateBound` or records a new event. There is no session-expiry, sign-out, or
presence table anywhere in the backend. "Bound" therefore means "has completed sign-in at
least once", not "is currently signed in" — collapsing it onto the design's "Signed in" label
would misstate live presence, and there is no timestamp available to honestly compute
"Signed out · 2 days ago" (that would require knowing *when the current session ended*, which
nothing records). Two honest states, correctly labelled, serve the screen's real purpose
(SC-001: at-a-glance review of who can and has signed in) without claiming information the
system doesn't have.

**Alternatives considered**:
- *Treat "bound" as "Signed in" and show `dateBound` relative-formatted as the design's third
  state whenever the label reads "Signed out"* — rejected: there's no way to distinguish
  "signed in right now" from "signed in once, months ago" using only `dateBound`, so this
  would always show one of two states under a misleading three-state UI, worse than being
  honest about having two.
- *Add live presence tracking (e.g. update `dateBound`-equivalent on every token validation, or
  track active sessions)* — rejected as new scope: this is a real feature (session/presence
  tracking) with its own security and performance considerations (write-on-every-request cost,
  definition of "currently signed in" for a stateless JWT-bearer API), and belongs in a
  separate spec, exactly as spec.md's Assumptions state.

## Decision 3: Expose `dateAdded` on the list endpoint

**Decision**: `_account_summary()` (`src/backend/api/admin/accounts.py`) serializes
`entry.dateAdded` as `"dateAdded"` on every account in `list_accounts`'s response. No format
conversion happens server-side — the ISO-8601 string already stored is passed through, and the
client formats it into the design's short form (e.g. `12 Aug`).

**Rationale**: `dateAdded` is already written on every entry (`add_or_merge`,
`ensure_seed_administrator`) and already returned by `add_account`'s response via the same
`_account_summary()` helper — it is simply missing from what `list_accounts` returns today, an
omission rather than a design decision. Exposing it is ordinary API-completion work, not new
data collection, and the *Scope note* explicitly carves this out as in-scope (FR-008).

**Alternatives considered**:
- *Format the date server-side (e.g. "12 Aug")* — rejected: the codebase's other short-date
  formatting (e.g. `AdminPage.jsx`'s `formatLastPublished`) is done client-side from an ISO
  string, and locale-aware short-date formatting is a presentation concern, not something the
  API should bake in.

## Decision 4: Vendor the shared button-language block additively

**Decision**: The block the canonical `styles.css` appends after its existing `.btn-primary`/
`.btn-secondary`/`.btn-ghost`/`.nav a` rules (a 2px visible border at rest on every button
variant, animated `background/color/border-color/box-shadow` transitions, and a nav
bottom-border affordance) is copied into `src/frontend/src/styles/designTokens.css` in the
same position — appended after the app's existing button rules, not replacing them, since
later same-specificity CSS rules win by source order and the canonical file's own diff against
the app's previously-vendored copy is purely additive (no rule removed).

**Rationale**: The issue states the updated `styles.css` "now encapsulates design language for
all buttons across the app" — this is explicitly meant to apply everywhere, not just to the
People screen, and constitution "UI Design System Requirements" requires the token stylesheet
be "copied in unmodified" from its vendored source. Appending in the same relative order the
canonical file uses keeps the vendored copy a faithful mirror, and since it's additive, no
other screen's markup needs a class rename to pick it up.

**Alternatives considered**:
- *Scope the new button treatment to the People screen only (a page-scoped override)* —
  rejected: the issue's own text and the canonical `styles.css`'s file-level change both say
  this is app-wide design language, and constitution Principle VIII forbids re-deriving or
  forking the token layer per screen.

## Decision 5: Role tag classes

**Decision**: `AccountList`'s role tags switch from the current `ROLE_TAG_CLASS` mapping
(`Administrator → tag tag-accent`, `Player → tag tag-neutral`) to the design spec's pairing:
`Player → tag tag-outline`, `Administrator → tag tag-accent` (§6 of `05-admin-users-spec.md`).

**Rationale**: `tag-outline` and `tag-accent` are both already-defined design-system classes
(used elsewhere, e.g. `AdminPage.jsx`'s published/unpublished tags use `tag-accent`/
`tag-neutral` similarly) — this is a one-line class-mapping change, not a new component.

**Alternatives considered**:
- *Keep `tag-neutral` for Player* — rejected: doesn't match the canonical design spec's
  explicit table (§6), and accent is reserved (constitution rule 4) for the Administrator tag,
  the signed-in dot, and the primary action — keeping Player as `tag-neutral` still separates
  it visually from Administrator's accent, so switching to `tag-outline` is purely a fidelity
  fix, not a functional one.
