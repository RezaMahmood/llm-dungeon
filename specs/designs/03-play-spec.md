# Play surface — design spec

Reference implementation: `screens/03-play.html`. Design system: **Modernist** (`screens/styles.css`).
App name: **LLM Dungeon**.

---

## 1. Purpose

The screen a player is on while playing a story. It shows the running transcript of the game,
takes the player's next move, and keeps the story's context (place, goal, progress, help) visible
without the player having to scroll for it.

The transcript is the only thing that moves. Everything else is pinned.

---

## 2. Page structure

Full-viewport, no page-level scroll. A `height: 100vh; overflow: hidden` flex column:

```
┌────────────────────────────────────────────────────────────┐
│ HEADER  LLM Dungeon │ The Lighthouse at Gullwing Cove      │  fixed
│                      Refresh  Save a checkpoint  Pause&exit│
├──────────────────────────────────────┬─────────────────────┤
│ 03                                   │ WHERE YOU ARE       │
│ CHAPTER THREE — THE KEEPER'S STAIRS  │ The keeper's stairs │
│                                      │ ───────────────     │
│ THE STORY                            │ YOUR GOAL           │
│ …150 words…                          │ Find out who has…   │  status
│ YOU                          scrolls │ ───────────────     │  panel,
│ look through the gap                 │ PROGRESS            │  fixed
│ THE STORY                            │ 3 of 5 chapters     │
│ …150 words…                          │ ▮▮▮▯▯               │
│                                      │ ───────────────     │
│                                      │ [Stuck? Get a hint] │
├──────────────────────────────────────┤ Saved automatically │
│ TRY [climb the stairs] [call out] …  │                     │  fixed
│ [ What do you do next?        ] [Go] │                     │
└──────────────────────────────────────┴─────────────────────┘
```

- **Header** — `flex: none`, `padding: 12px 20px`, `border-bottom: 2px solid var(--color-divider)`.
- **Body** — `display: grid; grid-template-columns: 1fr 292px; min-height: 0`.
  - Left cell is a flex column (`min-height: 0`) with `border-right: 2px solid var(--color-divider)`:
    scrolling transcript on top, fixed input dock below.
  - Right cell is the status panel.

`min-height: 0` on the grid and the left column is required or the transcript will push the
input dock off-screen instead of scrolling.

---

## 3. Header

| Item | Style |
| --- | --- |
| `LLM Dungeon` | link back to the story list; `var(--font-heading)`, 800, 15px, `var(--color-accent-700)` |
| vertical rule | 1px, `var(--color-divider)`, stretched to the header height |
| Story title | `var(--font-heading)`, 800, 17px, `margin-right: auto` |
| Refresh | `.btn .btn-ghost`, Lucide `refresh-cw` icon + label, 13px |
| Save a checkpoint | `.btn .btn-secondary` |
| Pause & exit | `.btn .btn-primary` — opens the pause dialog (§7) |

---

## 4. Transcript pane

`flex: 1; overflow-y: auto; padding: 32px 40px 20px`, content capped at `max-width: 64ch`.

Pinned at the top of the scroll content (scrolls away with it):

- Chapter numeral — `.ovnum`, 80px, `var(--color-accent-200)`, e.g. `03`.
- Chapter line — 12px, uppercase, `letter-spacing: 0.1em`, `var(--color-accent-700)`,
  `Chapter three — The keeper's stairs`.

Then the turn log, oldest first. Every entry is one block, `margin-bottom: 22px`:

- **Label** — 11px, uppercase, `letter-spacing: 0.1em`, `color-mix(in srgb, var(--color-text) 45%, transparent)`.
  Either `THE STORY` or `YOU`.
- **Body** — 19px, `line-height: 1.65`, `text-wrap: pretty`, `margin: 0`.
  Player entries are *italic*; story entries are roman.

Order: an opening story block, then for each turn a `YOU` block followed by a `THE STORY` block.
A story reply is roughly **150 words** — this is the length the layout must be designed against,
not a short teaser.

On load and after every new turn, scroll the pane to the bottom (`scrollTop = scrollHeight`)
so the newest text is visible without the player scrolling.

---

## 5. Input dock

`flex: none`, `border-top: 2px solid var(--color-divider)`, `padding: 16px 40px 22px`.
Always visible; never scrolls with the transcript.

**Suggested actions** — `display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px`:
a `TRY` label in the same 11px uppercase muted style, then up to three
`.btn .btn-secondary` chips at 13px / `padding: 8px 12px` carrying literal commands
("climb the stairs"). Clicking one submits it as the player's move.

**Command line** — `display: flex; gap: 10px`:
- `.input#cmd`, `flex: 1`, `min-height: 52px`, 18px, `padding: 10px 14px`,
  placeholder "What do you do next?", with a visually-hidden `<label>`.
- `.btn .btn-primary` "Go", `padding: 0 26px`, 16px.

**Spelling forgiveness** — a hidden 13px `var(--color-accent-700)` line under the form, revealed
only when the parser suspects a misspelling: *Did you mean **lighthouse**? Press Go again and
I'll take it either way.* The game never rejects a move outright for spelling.

---

## 6. Status panel

Fixed 292px right column, `padding: 24px 20px`, flex column, scrolls only if it overflows.
Section labels are the same 11px uppercase muted style; separators are `.hr` at `height: 1px`,
`margin: 20px 0`.

1. **Where you are** — location name, `var(--font-heading)`, 800, 22px.
2. **Your goal** — 15px, `line-height: 1.5`, one sentence.
3. **Progress** — `.ovnum` chapter number at 52px in `var(--color-accent)` with
   "of 5 chapters" 13px muted beside it, then a segment bar: flex row, `gap: 4px`,
   each segment `height: 8px; flex: 1`, completed `var(--color-accent)`, remaining
   `var(--color-neutral-300)`.
4. **Stuck? Get a hint** — `.btn .btn-secondary .btn-block`, label flush left,
   `padding: 14px`.
5. **"Saved automatically after every turn."** — 12px muted, pushed to the panel bottom with
   `margin-top: auto`.

---

## 7. Pause dialog

`.dialog-backdrop` + `.dialog`, hidden by default (`display: none`; shown by adding a `show`
class that sets `display: grid`). Width `min(520px, 100%)`, `padding: 32px`.

- `.ovnum` `II` at 72px in `var(--color-accent)`.
- `.dialog-title` 28px — "Paused".
- `.dialog-body` — "Your story is saved at the keeper's stairs. Come back whenever — nothing
  moves without you." The location is the live one.
- `.hr`, then two full-width buttons: `.btn-primary` "Keep playing" (closes the dialog) and a
  `.btn-secondary` link "Save and exit to my stories".

---

## 8. States to support

The prototype exposes a turn-count switcher (1 / 2 / 5 / 10) at the top of the page. It is a
**prototype affordance only** and must not ship. The states it demonstrates must all hold:

| Turns | What must be true |
| --- | --- |
| 1 | Transcript is short and sits at the top of the pane; no scrollbar on a desktop viewport. The dock and status panel look identical to every other state. |
| 2 | First signs of scrolling on shorter viewports; the newest reply is fully visible. |
| 5 | Pane scrolls; chapter numeral has scrolled out of view; the dock stays put. |
| 10 | Long transcript (~1,500 words). Scroll performance and the auto-scroll-to-bottom behaviour matter; nothing in the header, dock or status panel shifts or resizes. |

The layout must not change with transcript length — only the scroll position does.

---

## 9. Interaction

- Focus: `outline: 2px solid var(--color-accent); outline-offset: 2px` everywhere; never the
  browser default.
- Buttons carry a visible border at rest and fill `var(--color-accent)` with `var(--color-bg)`
  text on hover; pressed `var(--color-accent-600)`.
- Suggested-action chips highlight individually, not as a group.
- Submitting a move: append the `YOU` block immediately, then the story reply when it arrives;
  scroll to the bottom on each append. Disable Go and the chips while a reply is pending.
- Saving is automatic after every turn; "Save a checkpoint" creates a named restore point in
  addition to the autosave.

---

## 10. Design system rules that must hold

- Zero corner radius anywhere.
- All colour, type and spacing values come from `styles.css` custom properties.
- Button labels flush left inside wide/block buttons.
- Structural edges are 2px rules; in-panel separators are 1px.
- Accent red is reserved for the chapter numeral, progress fill, small kickers, hover and
  pressed states, and the single primary action.

---

## 11. Data contract

```ts
type Entry = { speaker: "story" | "player"; text: string };

type PlayView = {
  storyId: string;
  storyTitle: string;
  chapter: { number: number; total: number; title: string };
  location: string;        // "The keeper's stairs"
  goal: string;            // one sentence
  entries: Entry[];        // oldest first; story replies ~150 words
  suggestions: string[];   // up to 3 literal commands
  spellingHint?: { suggestion: string };
  pendingReply: boolean;
};
```

---

## 12. Out of scope

Responsive behaviour below desktop width, the hint content itself, checkpoint management UI,
and end-of-story / end-of-chapter screens.
