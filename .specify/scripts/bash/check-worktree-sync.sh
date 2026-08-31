#!/usr/bin/env bash
# PreToolUse guard for Edit|Write|NotebookEdit: blocks a file edit whose cwd
# has drifted away from the git worktree that .specify/feature.json (if any)
# says it should be on. Read-only, no-op when there's no feature.json here.
set -euo pipefail

FEATURE_JSON=".specify/feature.json"
if [[ ! -f "$FEATURE_JSON" ]]; then
  exit 0
fi

FEATURE_DIR="$(jq -r '.feature_directory // empty' "$FEATURE_JSON" 2>/dev/null || true)"
if [[ -z "$FEATURE_DIR" ]]; then
  exit 0
fi

EXPECTED_BRANCH="$(basename "$FEATURE_DIR")"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"

if [[ -z "$CURRENT_BRANCH" ]]; then
  # Not a git repo / detached in a way we can't resolve — nothing to compare.
  exit 0
fi

if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
  CWD="$(pwd)"
  echo "BLOCKED: cwd ($CWD) is on branch '$CURRENT_BRANCH' but its .specify/feature.json expects feature branch '$EXPECTED_BRANCH'." >&2
  echo "This session's working directory has drifted from its feature worktree — editing here would land changes on the wrong branch." >&2
  echo "Run /speckit-branch-ensure to move back to the correct worktree before editing." >&2
  exit 2
fi

# Belt-and-braces check for the per-worktree isolated-devcontainer workflow
# (see docs/WORKTREE_CONTAINER_WORKFLOW.md). bin/wt bakes WORKTREE_CONTAINER
# into the container's environment as the branch it was started for. If
# this session is running inside such a container, confirm that env var
# still matches the branch feature.json expects -- catches a session left
# running against a stale/wrong container, which the branch check above
# can't see (the container's git branch and feature.json are correct; only
# the container identity would be wrong).
if [[ -n "${WORKTREE_CONTAINER:-}" && "$WORKTREE_CONTAINER" != "$EXPECTED_BRANCH" ]]; then
  echo "BLOCKED: this container was started for worktree '$WORKTREE_CONTAINER' (WORKTREE_CONTAINER) but its .specify/feature.json expects feature branch '$EXPECTED_BRANCH'." >&2
  echo "This looks like the wrong container for this worktree — exit and run 'bin/wt $EXPECTED_BRANCH' instead." >&2
  exit 2
fi

exit 0
