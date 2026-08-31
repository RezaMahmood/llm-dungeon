#!/usr/bin/env bash
# Manual/cron safety-net sweep for the per-worktree devcontainer workflow
# (see docs/WORKTREE_CONTAINER_WORKFLOW.md). Run from the primary repo
# root, never from inside a worktree's own container -- this needs to see
# every worktree at once, which is exactly what an isolated worktree
# container cannot do.
#
# Deterministic and read-mostly: removes only containers whose
# devcontainer.local_folder points at a .worktrees/<branch> path that no
# longer has a registered git worktree. Never touches a container for a
# path that still has one, and never touches git state itself.
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository." >&2
  exit 1
fi

_common_dir="$(git rev-parse --git-common-dir)"
case "$_common_dir" in
  /*) : ;;
  *) _common_dir="$(pwd)/$_common_dir" ;;
esac
PRIMARY_REPO_ROOT="$(CDPATH= cd "$(dirname "$_common_dir")" && pwd)"
WORKTREES_ROOT="$PRIMARY_REPO_ROOT/.worktrees"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required on PATH." >&2
  exit 1
fi

mapfile -t LIVE_WORKTREES < <(
  git -C "$PRIMARY_REPO_ROOT" worktree list --porcelain \
    | awk '/^worktree /{print $2}'
)

is_live() {
  local candidate="$1"
  for wt in "${LIVE_WORKTREES[@]}"; do
    [[ "$wt" == "$candidate" ]] && return 0
  done
  return 1
}

FOUND_ANY=0
while IFS=$'\t' read -r container_id local_folder; do
  [[ -z "$container_id" ]] && continue
  case "$local_folder" in
    "$WORKTREES_ROOT"/*) : ;;
    *) continue ;;
  esac
  FOUND_ANY=1
  if is_live "$local_folder"; then
    echo "keep:   $local_folder ($container_id) -- worktree still registered"
  else
    echo "remove: $local_folder ($container_id) -- no registered worktree"
    docker rm -f "$container_id" >/dev/null
  fi
done < <(docker ps -a --filter "label=devcontainer.local_folder" \
            --format '{{.ID}}\t{{.Label "devcontainer.local_folder"}}')

if [[ "$FOUND_ANY" == "0" ]]; then
  echo "No worktree-labeled containers found under $WORKTREES_ROOT."
fi
