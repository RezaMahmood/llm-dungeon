# Quickstart: Sessions (Admin) Screen — Design Conformance and Session Deletion

## Automated validation (the gate)

```bash
# Backend — session deletion, the admin endpoint, and the session_removed split
pytest src/backend/tests

# Frontend — the restyled screen, the delete flow, and the player bump
npm --prefix src/frontend run test
npm --prefix src/frontend run lint
```

Run these in the devcontainer if one is up for this checkout
(`devcontainer exec --workspace-folder . -- <command>`); on the host otherwise.

The suites that must be green, and what each one is covering:

| Suite | Covers |
| --- | --- |
| `tests/unit/test_session_overview_service.py` | delete resolution across both containers, 404 when neither holds the id |
| `tests/unit/test_play_session_service.py` | `delete_session_as_administrator` deletes regardless of owner and of `status`; the owner-checked methods are unchanged |
| `tests/unit/test_test_play_session_service.py` | same, plus `Story.lastTestPlayedAt` untouched |
| `tests/integration/test_admin_sessions_endpoint.py` | admin-only DELETE, 200/404/403/401 |
| `tests/integration/test_game_sessions_*` | `session_removed` vs `story_deleted` told apart on all four player endpoints |
| `tests/components/AdminSessionsTable` + `tests/integration/admin_sessions.test.jsx` | heading counts, deleted-story label, token formatting, empty state, confirm-then-delete, failure and 404 paths |
| `tests/Play` + `tests/integration` home/game tests | the bump: play surface → `/menu` → dialog → dismissal |

## Manual walkthrough

### Prerequisites

- Cosmos DB emulator, Functions host, and Vite dev server running per the repo's normal local
  setup.
- Signed in as an account holding the Administrator role, with at least one played story so the
  list is not empty.

### The restyled screen

1. Go to **Sessions** (`/admin/sessions`) from the admin nav. Confirm the nav item is marked as
   the current page and the page itself has no page-level scrollbar — only the content area
   below the nav scrolls.
2. Confirm the `SESSIONS` kicker and a heading reading `{n} sessions across {m} stories`, with
   the counts matching the rows.
3. Confirm each row shows the story title, the full session UUID in monospace, a right-aligned
   thousands-separated token total, and the owning account.
4. Narrow the window and confirm the table wraps long UUIDs and addresses inside their cells
   rather than scrolling sideways, and that Delete stays reachable.

### States worth reaching deliberately

5. **Zero tokens** — start a story and leave it at turn 0; its row must show `0`, not a dash.
6. **Deleted story** — delete a story that has sessions; those rows must show `(deleted story)`
   in italic, must not be counted in the heading's story total, and must still be deletable.
7. **Empty** — delete every session; the heading must read `No sessions` and the table must be
   replaced by the explanatory sentence.

### Deleting

8. Select **Delete** on a row. Confirm nothing is deleted yet and the dialog names the session
   by its first 8 characters and its account, and says the action cannot be undone.
9. Choose **Keep it**; confirm the row is untouched and no row is left highlighted or pending.
10. Reopen and confirm **Delete session**; confirm the row disappears, the heading recomputes,
    and a reload shows the session is genuinely gone.
11. Delete an administrator **test-play** session the same way; confirm it deletes, and that the
    story it belonged to is still publishable afterwards (its `lastTestPlayedAt` is untouched).

### The player bump

12. In a second browser profile, sign in as a player and start a story — leave the play surface
    open mid-session.
13. As the administrator, delete that player's session from the Sessions screen.
14. Back in the player's window, type an instruction and submit. Confirm the player lands on the
    **Home** page with a dialog saying the session has been removed — not a message about the
    story being deleted, which is the bug this feature corrects.
15. Dismiss the dialog. Confirm Home is current and working, the deleted session is absent from
    **In progress**, and the story is available to start again from **Ready to play**.
16. Repeat reaching it from the other three actions — the header Refresh, a checkpoint save, and
    Resume from a stale Home tab left open since before the deletion. All four must behave the
    same.

### The regression that matters most

17. Delete a *story* (not a session) that a player has an open session for, and confirm that
    player still gets the **story deleted** message, not the session-removed one. The two
    outcomes were the same code path before this feature and must now be distinct.
</content>
