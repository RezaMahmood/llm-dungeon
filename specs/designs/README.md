# Lantern screen reference

Static HTML for the four surfaces, extracted from the hi-fi prototype (`Lantern.dc.html`).
Use these as the acceptance reference in the spec-kit spec.

    index.html             screen list
    01-login.html          Microsoft SSO
    02-story-select.html   in-progress, then unopened
    03-play.html           story pane + status panel + pause screen
    04-admin-wizard.html   six steps, world prompt step active
    05-admin-users.html    add player/administrator; per-row remove with confirm
    06-game-setup.html     start-new-game: adventure → character name → character type

## Copying into the repo

The folder is self-contained: `styles.css` (the Modernist design system, vendored) sits
alongside the pages and each page links it as `href="styles.css"`. Copy the whole `screens/`
folder and it works as-is. Nothing else is external — Archivo is imported by the stylesheet.

If you move the pages away from `styles.css`, repoint the `<link>` in all five.

## Navigation

One `.nav` bar, same markup on every signed-in surface.

- **Player:** My stories · Badges · Admin (staff only) — Sign out right-aligned, name chip last.
- **Admin:** Stories · New story · People, a 1px vertical divider, then Player view — Sign out
  right-aligned, name chip last. The current page carries `aria-current="page"`.
- **Play (03)** is the exception: the full nav is replaced by a compact title bar so the story
  keeps the height. The `Lantern` mark at its left returns to story select.

## Notes for implementers

- **Scroll contract (Article V):** the shell is `height:100vh; overflow:hidden`. On 03 only
  `.storyscroll` scrolls; title bar, input row and status panel are fixed.
- **Pause screen** on 03 is inert markup toggled by a class (`.pause.show`) so it can be
  inspected without a framework. Real implementation owns this state.
- **Hidden blocks** marked `hidden` are alternate states kept in place for reference: the
  spelling-forgiveness hint on 03, and step 05 (test play) on 04.
- **Game setup (06):** extends 02's "Start something new" card grid with two more steps
  (character name, character type), using the same oversized-numeral step-bar pattern as
  04's wizard. Steps 2–3 only become available once an adventure is chosen (006-adventure-
  and-character-setup FR-003a); changing the adventure clears any chosen character type but
  keeps the name (FR-004a). A single character type is still shown as an explicit radio
  choice, never auto-selected. Introduced by `006-adventure-and-character-setup` — see that
  spec's Constitution Principle XI sign-off task before treating this as final.
- **People (05):** roles are Player and/or Administrator — an account may hold both, so the
  role field is checkboxes, not a segmented control, and at least one must be selected. Accounts are Microsoft identities —
  no password field anywhere. Removal is one account at a time, always behind the confirm
  dialog (`.confirm.show`); there is no bulk selection by design. The list is sorted alphabetically
  by email, and an account that has never completed sign-in shows a status of "Pending first
  sign-in" (sign-off recorded in `014-account-listing`'s tasks.md T001; not depicted in this
  static mockup).
- **No prototype screen for `012-story-editing-and-review`:** its administrator story list and
  read-only story-configuration viewer are deliberately absent here. Per that spec's FR-012 and
  the user decision of 2026-09-06, both ship as plain, unstyled pages built only from
  design-system classes and token-based styles — no mockup is expected, and their absence from
  this reference is not an omission to be fixed before implementation. Visual styling is
  follow-up work; the accessibility bar still applies in full. The wizard those screens link to
  is 04, unchanged. Their **behavioral** contract is not absent: constitution v2.1.0 adds an
  "Administrator — stories & configuration" screen contract (a contract without a prototype,
  which that section now explicitly permits), and that text is the acceptance reference for
  these two screens until a prototype is drawn.
- **Test play (04, step 05):** the "Flag this reply" button is deliberately not implemented —
  `010-story-test-play-done` specifies no in-session flagging; a problem found while testing is fixed
  by editing the story afterwards through the wizard. "Restart test" is implemented, but aborts
  rather than resets: after a warning, the session is deleted and the administrator returns to
  the edit story page. A session that reaches one of the story's endings offers Publish (with
  confirmation) and Edit instead. That screen's visual design is deferred per `010` FR-011.

- **Suggested actions** on 03 are required, not decorative — a player who cannot spell must
  still be able to progress.
- **Stories in progress (02, section 2):** built by `009-save-and-continue` — the ordinal
  rows, "chapter · last played · location" meta line, progress bars, and Resume action map
  to `StoriesInProgress`/`SavedGameRow`. Resume skips the `POST .../resume` call entirely
  when the row is already the player's active game (FR-001a).
- **Checkpoint save (03):** the header's "Save a checkpoint" button — inert in
  `008-core-gameplay-done` — is wired up by `009-save-and-continue` (FR-003): it records a
  server-labelled, timestamped marker and shows a brief visible confirmation, with no new
  chrome added to this screen.
- No inline classes were invented beyond three utilities in each page's `<style>`
  (`.ovnum`, `.rowhov`, `.storyscroll`); everything else is a design-system class or a
  token-based inline style.
