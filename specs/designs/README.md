# Lantern screen reference

Static HTML for the four surfaces, extracted from the hi-fi prototype (`Lantern.dc.html`).
Use these as the acceptance reference in the spec-kit spec.

    index.html             screen list
    01-login.html          Microsoft SSO
    02-story-select.html   in-progress, then unopened
    03-play.html           story pane + status panel + pause screen
    04-admin-wizard.html   six steps, world prompt step active

## Copying into the repo

The folder is self-contained: `styles.css` (the Modernist design system, vendored) sits
alongside the pages and each page links it as `href="styles.css"`. Copy the whole `screens/`
folder and it works as-is. Nothing else is external — Archivo is imported by the stylesheet.

If you move the pages away from `styles.css`, repoint the `<link>` in all five.

## Spec references

Each screen is the acceptance reference for one or more feature specs under `specs/`.
Where implementation and screen disagree, the screen wins on layout and copy; the
constitution's UI Design System Requirements win on rules (see `.specify/memory/constitution.md`).

| Screen | Spec(s) |
| --- | --- |
| `index.html` | Site index only — no dedicated spec; see the four screens below. |
| `01-login.html` | [`002-login-and-access-control`](../002-login-and-access-control-done/spec.md) |
| `02-story-select.html` | [`006-adventure-and-character-setup`](../006-adventure-and-character-setup/spec.md) ("Start something new") · [`009-save-and-continue`](../009-save-and-continue/spec.md) ("stories in progress" / Resume) |
| `03-play.html` | [`008-core-gameplay`](../008-core-gameplay/spec.md) (story pane, status panel, hint) · [`009-save-and-continue`](../009-save-and-continue/spec.md) (checkpoint save, pause & exit, autosave) |
| `04-admin-wizard.html` | [`004-story-creation-done`](../004-story-creation-done/spec.md) (steps 01–04: name & cover, world & setting, tone & reading level, session length) · [`010-story-test-play`](../010-story-test-play/spec.md) (step 05: test play) · [`005-story-publishing`](../005-story-publishing/spec.md) (step 06: publish) |

**Resolved gaps**:

- **Test play** (`04-admin-wizard.html`, step 05): now specified in
  [`010-story-test-play`](../010-story-test-play/spec.md); the publish-blocking gate that
  originally accompanied it is now its own spec,
  [`017-story-publish-test-play-gate`](../017-story-publish-test-play-gate/spec.md)
  (split 2026-08-29), which `005-story-publishing` references (its FR-008).
- **"Publish & assign"** (`04-admin-wizard.html`, step 06): resolved by explicit product
  decision — there is no assignment/targeting capability. Publishing makes a story
  available to every player; `005-story-publishing`'s FR-009 makes this explicit. The
  screen's "assign" label names no separate feature.

**Gaps found while cross-referencing** (screen shows a capability no current spec
covers — flagged here, not yet specified):

- **Hint action** (`03-play.html`, "Stuck? Get a hint"): not covered by
  `008-core-gameplay`, which specifies narrative responses to player actions but no
  separate hint mechanism.
- **Reading level / chapter count as story metadata** (`02-story-select.html` cards,
  `04-admin-wizard.html` step 04 "Chapters" field): shown in the design but not named as
  a Key Entity attribute in `004-story-creation-done` or `006-adventure-and-character-setup`.

## Notes for implementers

- **Scroll contract (Article V):** the shell is `height:100vh; overflow:hidden`. On 03 only
  `.storyscroll` scrolls; title bar, input row and status panel are fixed.
- **Pause screen** on 03 is inert markup toggled by a class (`.pause.show`) so it can be
  inspected without a framework. Real implementation owns this state.
- **Hidden blocks** marked `hidden` are alternate states kept in place for reference: the
  spelling-forgiveness hint on 03, and step 05 (test play) on 04.
- **Suggested actions** on 03 are required, not decorative — a player who cannot spell must
  still be able to progress.
- No inline classes were invented beyond three utilities in each page's `<style>`
  (`.ovnum`, `.rowhov`, `.storyscroll`); everything else is a design-system class or a
  token-based inline style.
