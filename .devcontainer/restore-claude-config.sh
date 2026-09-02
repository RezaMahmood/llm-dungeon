#!/usr/bin/env bash
# postStartCommand for .devcontainer/devcontainer.json.
#
# ~/.claude.json carries Claude Code's oauth account/onboarding state and
# used to be bind-mounted read-write directly at that path. Its atomic save
# (write a backup, write a temp file, rename() over the real path) doesn't
# survive a single-file bind mount under Docker Desktop's virtiofs -- a
# save from *any* side (host, or any one of several concurrently-running
# worktree containers, since the file was shared read-write across all of
# them) could truncate the host's real ~/.claude.json to 0 bytes instead of
# atomically replacing it, corrupting the live config for every other
# session sharing it.
#
# Fix: devcontainer.json now mounts the host file read-only at
# ~/.claude.json.host, and this script (which runs on every container
# start, not just creation, unlike postCreateCommand) copies it into the
# container's own real ~/.claude.json -- an ordinary in-container file, not
# a mount -- every time. The container can no longer write back through to
# the host file at all, so it can't corrupt it. See docs/WORKTREE_CONTAINER_WORKFLOW.md.
set -euo pipefail

HOST_SOURCE="/home/vscode/.claude.json.host"
CONFIG="/home/vscode/.claude.json"

if [[ ! -f "$HOST_SOURCE" ]]; then
  echo "restore-claude-config: $HOST_SOURCE not mounted -- nothing to sync." >&2
  exit 0
fi

if [[ ! -s "$HOST_SOURCE" ]]; then
  echo "restore-claude-config: $HOST_SOURCE is empty on the host -- leaving this container's $CONFIG untouched." >&2
  exit 0
fi

cp "$HOST_SOURCE" "$CONFIG"
