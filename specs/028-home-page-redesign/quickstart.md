# Quickstart: Validating the Player Home Page Redesign

## Prerequisites

- Local offline test harness running (`027-local-offline-test-harness`) or the devcontainer
  with backend + frontend dev servers up.
- At least one published story with a `blurb` set via the admin wizard, and one signed-in
  player account (per existing `003-account-provisioning` seed data / test fixtures).

## Backend validation

```bash
devcontainer exec --workspace-folder . -- pytest src/backend/tests/services/test_play_session_service.py -k delete_player_session
devcontainer exec --workspace-folder . -- pytest src/backend/tests/api/game/test_sessions.py -k delete
devcontainer exec --workspace-folder . -- pytest src/backend/tests/services/test_story_service.py -k blurb
devcontainer exec --workspace-folder . -- pytest src/backend/tests/services/test_story_draft_service.py -k blurb
```

Expected: a player can delete only their own session (403 for another player's, 404 for a
missing one, 204 on success); `blurb` round-trips through draft PATCH → publish →
`list_published_summaries` → configuration export/import.

## Frontend validation

```bash
devcontainer exec --workspace-folder . -- npm --prefix src/frontend test -- Home
devcontainer exec --workspace-folder . -- npm --prefix src/frontend test -- GamePage
```

Expected: `HomePage` renders the welcome band, both columns, and all six states from
spec.md §6 (via mocked `gameService` responses); `GamePage` no longer renders
`StoriesInProgress`/`AdventureList` and starts directly at character-name entry when handed
a pre-chosen adventure id.

## Manual end-to-end scenario (dev server)

1. Sign in as a player with no saved sessions. **Expect**: Home shows the zero-state lede
   and every published story in "Ready to play".
2. Click **Play** on a story. **Expect**: character-name step opens directly — no
   adventure-picker step. Complete setup; a new session starts.
3. Return to Home (`/menu`). **Expect**: that story now appears as a card in "In progress"
   with `Chapter 1`, and no longer appears in "Ready to play".
4. Click **Delete** on that card, confirm. **Expect**: the card disappears, "In progress"
   falls back to its zero state, and the story reappears in "Ready to play".
5. Sign in as an administrator (with player capability). **Expect**: identical page, plus
   "New story"/"Users" nav links and an "· Administrator" name-chip suffix.
6. Resize to 360px width. **Expect**: single-column layout, no horizontal scroll, Play/
   Resume/Delete all reachable and ≥44px tall.
