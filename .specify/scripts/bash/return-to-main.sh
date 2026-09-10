#!/usr/bin/env bash
# SessionStart / SessionEnd hook: keeps the PRIMARY checkout parked on the
# trunk between sessions.
#
# Feature work belongs in a worktree under .worktrees/ (see
# docs/WORKTREE_CONTAINER_WORKFLOW.md), so the primary checkout should be
# sitting on main whenever nobody is actively using it. In practice it was
# left on whatever branch was last worked on there, which is how a later
# session — or a `bin/wt` run resolving `--base=main` — silently picked up
# the wrong starting point (issue #293, problem 3).
#
#   SessionEnd   -> switch back to main when it is safe to do so.
#   SessionStart -> report, never switch. A session that starts on a
#                   non-trunk branch was put there deliberately (or
#                   SessionEnd could not clean up because the tree was
#                   dirty); silently moving HEAD out from under it would be
#                   worse than saying so.
#
# No-op inside a worktree container or a linked worktree: those exist to
# stay on their own branch.
set -euo pipefail

TRUNK="main"

# Hook payload arrives as JSON on stdin. Fall back to $1 so the script can
# be exercised directly (and by scripts/workflow-checks/test-hook-scripts.sh).
EVENT=""
if [[ -n "${1:-}" ]]; then
  EVENT="$1"
else
  _payload="$(cat 2>/dev/null || true)"
  if [[ -n "$_payload" ]]; then
    EVENT="$(printf '%s' "$_payload" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"
  fi
fi

# Inside a per-worktree container: not our business.
if [[ -n "${WORKTREE_CONTAINER:-}" ]]; then
  exit 0
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# A linked worktree's --git-dir is <common>/worktrees/<name>; only the
# primary checkout has the two equal.
GIT_DIR="$(git rev-parse --path-format=absolute --git-dir 2>/dev/null || true)"
GIT_COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
if [[ -z "$GIT_DIR" || "$GIT_DIR" != "$GIT_COMMON_DIR" ]]; then
  exit 0
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ -z "$CURRENT_BRANCH" || "$CURRENT_BRANCH" == "$TRUNK" ]]; then
  exit 0
fi

if [[ "$EVENT" == "SessionStart" ]]; then
  echo "Note: this primary checkout is on branch '$CURRENT_BRANCH', not '$TRUNK'. Feature work belongs in its own worktree — start one with 'bin/wt $CURRENT_BRANCH'. This session is NOT being moved; switch deliberately if that was not intended."
  exit 0
fi

# --- SessionEnd: return to trunk if that is safe ----------------------------
if ! git show-ref --verify --quiet "refs/heads/$TRUNK"; then
  echo "Left on '$CURRENT_BRANCH': no local '$TRUNK' branch to return to."
  exit 0
fi

for _marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
  if [[ -e "$GIT_COMMON_DIR/$_marker" ]]; then
    echo "Left on '$CURRENT_BRANCH': a rebase/merge/bisect is still in progress."
    exit 0
  fi
done

if [[ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]]; then
  echo "Left on '$CURRENT_BRANCH': uncommitted tracked changes present. Commit or stash them, then 'git switch $TRUNK'."
  exit 0
fi

if git switch "$TRUNK" >/dev/null 2>&1; then
  echo "Returned the primary checkout to '$TRUNK' (was on '$CURRENT_BRANCH')."
else
  echo "Left on '$CURRENT_BRANCH': 'git switch $TRUNK' failed."
fi

exit 0
