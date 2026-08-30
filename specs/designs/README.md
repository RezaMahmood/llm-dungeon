# Lantern screen reference

Static HTML for the four surfaces, extracted from the hi-fi prototype (`Lantern.dc.html`).
Use these as the acceptance reference in the spec-kit spec.

    index.html             screen list
    01-login.html          Microsoft SSO
    02-story-select.html   in-progress, then unopened
    03-play.html           story pane + status panel + pause screen
    04-admin-wizard.html   six steps, world prompt step active
    05-admin-users.html    add player/administrator; per-row remove with confirm

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

## Refresh

A ghost **Refresh** button (Lucide `refresh-cw` + label) sits right of the nav links on 02, 04
and 05, and in the title bar on 03. Same treatment everywhere; it re-fetches the current view
and never navigates.

## Notes for implementers

- **Scroll contract (Article V):** the shell is `height:100vh; overflow:hidden`. On 03 only
  `.storyscroll` scrolls; title bar, input row and status panel are fixed.
- **Pause screen** on 03 is inert markup toggled by a class (`.pause.show`) so it can be
  inspected without a framework. Real implementation owns this state.
- **Hidden blocks** marked `hidden` are alternate states kept in place for reference: the
  spelling-forgiveness hint on 03, and step 05 (test play) on 04.
- **People (05):** roles are Player and/or Administrator — an account may hold both, so the
  role field is checkboxes, not a segmented control, and at least one must be selected. Accounts are Microsoft identities —
  no password field anywhere. Removal is one account at a time, always behind the confirm
  dialog (`.confirm.show`); there is no bulk selection by design.
- **Suggested actions** on 03 are required, not decorative — a player who cannot spell must
  still be able to progress.
- No inline classes were invented beyond three utilities in each page's `<style>`
  (`.ovnum`, `.rowhov`, `.storyscroll`); everything else is a design-system class or a
  token-based inline style.
