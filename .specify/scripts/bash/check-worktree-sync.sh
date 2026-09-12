#!/usr/bin/env bash
# PreToolUse guard for Edit|Write|NotebookEdit: refuses an edit whose
# working directory has drifted away from the branch this session is
# supposed to be on. Read-only; it never changes git state.
#
# Two independent checks, in order of how widely they apply:
#
#  1. Session identity vs HEAD -- runs on EVERY branch. bin/wt sets
#     WORKTREE_CONTAINER to the branch the session was started for, so a
#     session started by bin/wt always has something to compare HEAD
#     against. It is set for a --no-container session on the host too,
#     not just inside a container: those run on exactly the chore/*,
#     fix/*, docs/* and perf/* branches this check exists for, and without
#     it the check would be dead on all of them. (The variable keeps its
#     container-era name because containers already built have it baked
#     into their environment; renaming it would disarm this check for
#     every live session until each one was rebuilt.) This is the check
#     that used to be unreachable: the script exited 0 before it whenever
#     .specify/feature.json was absent, which is every chore/*, fix/*,
#     perf/* and issue/* worktree (see issue #293, Leak B).
#
#  2. feature.json expectation vs HEAD -- speckit feature branches only,
#     where .specify/feature.json names the feature directory whose
#     basename is the branch that directory's work belongs on.
#
# Both are skipped mid-rebase/merge: HEAD is legitimately detached or
# moving then, and blocking edits during conflict resolution would break
# the very operation that brings a stale worktree back in line with main.
set -euo pipefail

block() {
  printf '%s\n' "$@" >&2
  exit 2
}

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || true)"
if [[ -z "$GIT_DIR" ]]; then
  # Not a git repository -- nothing to compare against.
  exit 0
fi

# A rebase, merge, cherry-pick or bisect in progress moves or detaches HEAD
# by design. Comparing against it would block conflict resolution, so stand
# down until the operation finishes.
for _marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
  if [[ -e "$GIT_DIR/$_marker" ]]; then
    exit 0
  fi
done

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
[[ "$CURRENT_BRANCH" == "HEAD" ]] && CURRENT_BRANCH=""

CONTAINER_BRANCH="${WORKTREE_CONTAINER:-}"

# --- Check 1: this container was started for one branch ---------------------
if [[ -n "$CONTAINER_BRANCH" ]]; then
  if [[ -z "$CURRENT_BRANCH" ]]; then
    block \
      "BLOCKED: this session was started for worktree '$CONTAINER_BRANCH' (WORKTREE_CONTAINER) but HEAD is detached." \
      "Edits made here would not land on '$CONTAINER_BRANCH' — they would be stranded on a detached HEAD." \
      "Run 'git switch $CONTAINER_BRANCH' before editing."
  fi
  if [[ "$CONTAINER_BRANCH" != "$CURRENT_BRANCH" ]]; then
    block \
      "BLOCKED: this session was started for worktree '$CONTAINER_BRANCH' (WORKTREE_CONTAINER) but HEAD is on branch '$CURRENT_BRANCH'." \
      "Editing here would land this worktree's changes on the wrong branch." \
      "Run 'git switch $CONTAINER_BRANCH' before editing, or exit and start the right worktree with 'bin/wt $CURRENT_BRANCH'."
  fi
fi

# --- Check 2: .specify/feature.json names the expected feature branch -------
FEATURE_JSON=".specify/feature.json"
if [[ ! -f "$FEATURE_JSON" ]]; then
  exit 0
fi

FEATURE_DIR="$(jq -r '.feature_directory // empty' "$FEATURE_JSON" 2>/dev/null || true)"
if [[ -z "$FEATURE_DIR" ]]; then
  exit 0
fi

EXPECTED_BRANCH="$(basename "$FEATURE_DIR")"

if [[ -z "$CURRENT_BRANCH" ]]; then
  # Detached HEAD outside a worktree container and outside a rebase/merge:
  # nothing reliable to compare, and check 1 already covers the container case.
  exit 0
fi

if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  block \
    "BLOCKED: cwd ($(pwd)) is on branch '$CURRENT_BRANCH' but its .specify/feature.json expects feature branch '$EXPECTED_BRANCH'." \
    "This session's working directory has drifted from its feature worktree — editing here would land changes on the wrong branch." \
    "Run /speckit-branch-ensure to move back to the correct worktree before editing."
fi

exit 0
