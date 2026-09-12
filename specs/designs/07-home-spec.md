# Home page — design spec

Reference implementation: `07-home.html`. Design system: **Modernist** (`styles.css`).
App name: **LLM Dungeon**.

---

## 1. Purpose

The page a user lands on immediately after signing in, for both roles. It answers two questions:
what am I part-way through, and what can I start? The only role difference is which links appear
in the navigation bar.

---

## 2. Page structure

Full-viewport, no page-level scroll on desktop/tablet. Three stacked bands inside a
`height: 100vh; overflow: hidden` flex column:

1. **Navigation bar** — fixed height, never scrolls.
2. **Welcome band** — fixed height, never scrolls.
3. **Two-column body** — fills remaining height; each column scrolls independently.

```
┌───────────────────────────────────────────────────────────┐
│ NAV: LLM Dungeon | Home My stories Badges [admin links]   │
│                              Refresh | Sign out | Ada B.  │
├───────────────────────────────────────────────────────────┤
│ WEDNESDAY AFTERNOON                                       │  tinted band
│ Welcome back, Ada.                                        │
│ You have one story on the go. Everything is saved…        │
├──────────────────────────────────┬────────────────────────┤
│ START SOMETHING NEW              │ KEEP GOING             │  fixed heads
│ Ready to play                    │ In progress            │
├──────────────────────────────────┼────────────────────────┤
│ list row            [ Play ]     │ ┌ card ─────────────┐  │  independent
│ ───────────────────────────────  │ │      [ Resume ]   │  │  scrollers
│ list row            [ Play ]     │ └───────────────────┘  │
│ …                                │ …                      │
└──────────────────────────────────┴────────────────────────┘
```

---

## 3. Navigation bar

Modernist `.nav`, background `var(--color-bg)`, no gap between items.

| Item | Visible to | Notes |
| --- | --- | --- |
| `LLM Dungeon` brand | all | `.nav-brand`, 28px right margin |
| Home | all | `aria-current="page"` on this page |
| My stories | all | |
| Badges | player + admin | |
| New story | **administrators only** | links to the admin wizard |
| Users | **administrators only** | links to user management |
| Refresh | all | `.btn .btn-ghost` with the Lucide `refresh-cw` icon + label, pushed right with `margin-left:auto` |
| Sign out | all | |
| Name chip | all | `.tag .tag-neutral`, reads `Ada B. · Player` or `Ada B. · Administrator` |

Role is the **only** differentiator: an administrator sees two extra links and a different role
suffix on the name chip. Nothing else on the page changes by role.

> Implementation note (`028-home-page-redesign`): this repo's shipped nav additionally retains
> an "Admin" link to the pre-existing admin story list for administrators, and renders "My
> stories" as an inert placeholder pending a future feature — see that feature's research.md
> Decisions 7 and 11, and `specs/designs/README.md`.

---

## 4. Welcome band

- Background `var(--color-neutral-200)`, bottom edge `2px solid var(--color-divider)`.
  This band edge is the page's only horizontal rule above the columns — do not add another.
- Padding `20px 32px 18px` (desktop).
- Kicker: 12px, uppercase, `letter-spacing: 0.1em`, `var(--color-accent-700)` — contextual, e.g. `WEDNESDAY AFTERNOON`.
- Heading: 28px, `var(--font-heading)`, weight 800, `line-height: 1.05` — `Welcome back, {firstName}.`
- Lede: 14px, muted, `max-width: 64ch`, driven by the in-progress count:
  - 0 — "Nothing on the go right now. Pick a story to start and it will save itself as you play."
  - 1 — "You have one story on the go. Everything is saved where you left it."
  - n — "You have {n} stories on the go. Everything is saved where you left it."

Keep this band deliberately small; it must not compete with the two lists.

---

## 5. Two-column body

`display: grid; grid-template-columns: 2fr 1fr;` filling the remaining height (`min-height: 0`
on the grid and both columns so the inner scrollers work).

Each column is a flex column of:
- **Column head** (`flex: none`, padding `26px 32px 16px`) — kicker + 24px heading, no rule underneath.
- **Column body** (`flex: 1; min-height: 0; overflow: auto`, padding `0 32px 48px`).

Left column has `border-right: 2px solid var(--color-divider)`.

### 5.1 Left column — "Ready to play"

Head: kicker `START SOMETHING NEW`, heading `Ready to play` (24px). Heading text does not
change with count.

One item per row, full column width, separated by `1px solid var(--color-divider)`:

```
grid-template-columns: 1fr auto;
align-items: start;  (button uses align-self: end)
padding: 20px 8px 33px;
min-height: 174px; box-sizing: border-box;
```

Row content, left cell:
- kicker `.card-kicker` — `{Genre} · {duration} min`
- title — `var(--font-heading)`, 800, 22px, `line-height: 1.15`
- blurb — 15px, `max-width: 60ch`, one sentence or two
- `.card-meta` — `Reading level: Year n`

Right cell: `.btn .btn-secondary`, label **Play**, `padding: 11px 16px`, bottom-aligned.

The whole row is a single `<a>` to the play surface; the button is a `<span>` inside it.

### 5.2 Right column — "In progress"

Head: kicker `KEEP GOING`, heading `In progress` (24px); when the list is empty the heading
reads `Nothing in progress` instead.

One **card** per row: `height: 158px`, `margin-top: 16px` (first card `0`),
`padding: 18px`, `box-shadow: 0 0 0 1px var(--color-divider)`, background `var(--color-bg)`,
`display: flex; flex-direction: column; overflow: hidden`.

Card content, in order:
1. Title — 19px, 800, clamped to two lines (`-webkit-line-clamp: 2`, fixed 44px box).
2. Meta — 12px muted, `margin-top: 4px`: `Chapter n · Last played {when} · {location}`.
3. Progress bar — `margin-top: 8px`, a flex row of `total` segments, `gap: 4px`, each `height: 6px; flex: 1`;
   completed segments `var(--color-accent)`, remaining `var(--color-neutral-300)`.
4. `.btn .btn-secondary` label **Resume**, 13px, `padding: 9px 14px`, and a **Delete** button
   (`.btn-danger`: 2px divider border, muted ink, Lucide `trash-2` icon + label, `padding: 9px 12px`)
   beside it in a `display: flex; gap: 8px` action row pushed to the card bottom with
   `margin-top: auto`.

Delete removes the player's saved session for that story. It must `preventDefault`/`stopPropagation`
so it does not trigger the card's resume link, and must confirm first —
"Delete your saved session for “{title}”? Your progress will be lost." On confirm the card is
removed and the story returns to the ready-to-play column; if it was the last session, the column
falls back to the zero state (§6 state 1). Delete never removes the story from the catalogue.

> Implementation note (`028-home-page-redesign`): the confirmation above is shown in the
> product's own design-system dialog, not a browser `confirm()` — see that feature's
> research.md Decision 6.

Whole card is an `<a>` to the play surface, resuming at the saved point.

### 5.3 Cross-column alignment (required)

The two lists share a **174px row pitch** so Play and Resume line up down the page:

- list row: `min-height: 174px` including its 1px bottom border (`box-sizing: border-box`)
- card: `158px` height + `16px` top margin = 174px

Both buttons sit the same distance from the bottom of their row: the card's Resume is pinned by
`margin-top: auto` above the 18px bottom padding; the row's Play is `align-self: end` above a
33px bottom padding. Both column bodies start at the same y because both column heads use the
same padding and the same 24px heading size. If any of these values change, re-check that the
buttons still align.

---

## 6. States to support

| # | State | Rendering |
| --- | --- | --- |
| 1 | No stories in progress | Right head reads `Nothing in progress`; body shows one paragraph, 15px, `padding: 28px 8px`: "When you open a story it lands here, so you can pick it straight back up next time." No card, no button. Lede uses the zero-state copy. |
| 2 | One in progress | Single card, no other change. |
| 3 | Many in progress | Cards stack at the 174px pitch; column scrolls. |
| 4 | One available | Single list row. |
| 5 | Many available | Rows stack; column scrolls. |
| 6 | Overflow (10+ either side) | No layout change — each column scrolls on its own; the nav and welcome band stay fixed. |

There is no "no stories available" state in scope; the catalogue always has at least one story.

---

## 7. Responsive behaviour

| Breakpoint | Layout |
| --- | --- |
| **Desktop** > 1100px | `2fr / 1fr` columns, page padding 32px, welcome heading 28px. |
| **iPad** ≤ 1100px | Columns become `3fr / 2fr`; horizontal padding drops to 24px; welcome padding `16px 24px 14px`. |
| **Mobile** ≤ 760px | Single column, page-level scrolling (`html, body { height: auto }`, `.shell { height: auto; overflow: visible }`). Left column loses its right border; the in-progress column gains `border-top: 2px solid var(--color-divider)`. List rows collapse to one column with the button left-aligned beneath the text (`justify-self: start`); fixed row heights and the title clamp are removed. Padding 18px. Nav wraps. |

Touch targets stay at or above 44px on mobile.

---

## 8. Interaction

- Hovering a row or card tints it `color-mix(in srgb, var(--color-text) 5%, transparent)`.
- Every button carries a visible 2px border at rest.
  - `.btn-secondary` fills `var(--color-accent)` with `var(--color-bg)` text on hover; pressed
    `var(--color-accent-600)`.
  - On the left column, hovering anywhere in a list row also highlights its **Play** button —
    the row has a single action, so row and button read as one target.
  - On in-progress cards this does **not** apply: **Resume** and **Delete** each highlight only
    when hovered directly, so a card with two actions never suggests which one is about to fire.
  - `.btn-primary` deepens to `var(--color-accent-600)` with a 3px accent halo on hover; pressed
    `var(--color-accent-700)`.
  - `.btn-ghost` reveals an accent border on hover.
  - `.btn-danger` (Delete) sits quiet at rest — divider-grey 2px border, muted ink — and fills
    `var(--color-accent)` with `var(--color-bg)` text on hover; pressed `var(--color-accent-600)`.
    It is never red at rest.
- Nav links show an accent underline on hover and for `aria-current="page"`.
- Focus: `outline: 2px solid var(--color-accent); outline-offset: 2px` — never the browser default.
- No button on the page is permanently filled red; the accent is reserved for hover, the progress
  bars and the small kickers.

---

## 9. Design system rules that must hold

- Zero corner radius anywhere.
- All colour, type, spacing values come from `styles.css` custom properties — no literal hex or
  font names.
- Button labels are flush left inside wide buttons.
- Headings and copy flush left; nothing centred.
- Rules are 2px for structural edges, 1px for list separators. Do not add rules that duplicate an
  existing edge (this is why the column heads carry no underline).
- Accent red is used sparingly: kickers, progress fill, hover and pressed states.

---

## 10. Data contract

```ts
type Session = {          // in progress
  id: string;
  title: string;
  chapter: number;
  lastPlayed: string;     // preformatted, e.g. "yesterday", "Friday", "3 weeks ago"
  location: string;       // e.g. "The keeper's stairs"
  completed: number;      // filled progress segments
  total: number;          // total segments
};

type Story = {            // ready to play
  id: string;
  genre: string;          // "Mystery" | "Adventure" | "Silly" | "Science" | …
  minutes: number;
  title: string;
  blurb: string;
  readingLevel: string;   // e.g. "Year 5"
};

type HomeView = {
  user: { firstName: string; displayName: string; isAdministrator: boolean };
  greetingKicker: string; // e.g. "Wednesday afternoon"
  sessions: Session[];    // newest activity first
  stories: Story[];       // catalogue order
};
```

Sessions sort by most recently played. Stories already started do **not** appear in the
ready-to-play list.

---

## 11. Out of scope

Badges, search and filtering of the catalogue, per-story detail pages, and any admin surface —
all reached from the nav, specified elsewhere.
