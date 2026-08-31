#!/usr/bin/env bash
# postStartCommand for .devcontainer/devcontainer.json.
#
# ~/.claude.json is bind-mounted into every worktree container as a single
# file (not a directory), so Claude Code's atomic save (write a backup,
# write a temp file, rename() over the real path) can leave this
# container's view of the mount stale or missing -- Docker Desktop's
# virtiofs/osxfs bind mounts track single files by identity at mount time
# and can't always follow a rename across it. Directory mounts (like
# ~/.claude, which is where the backups below live) don't have this
# problem. See docs/WORKTREE_CONTAINER_WORKFLOW.md.
#
# This runs on every container start (not just creation, unlike
# postCreateCommand) and self-heals by restoring the newest backup if the
# live file is missing.
set -euo pipefail

CONFIG="/home/vscode/.claude.json"
BACKUP_DIR="/home/vscode/.claude/backups"

if [[ -f "$CONFIG" ]]; then
  exit 0
fi

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "restore-claude-config: $CONFIG missing and no backup directory found at $BACKUP_DIR -- nothing to restore." >&2
  exit 0
fi

LATEST_BACKUP="$(ls -t "$BACKUP_DIR"/.claude.json.backup.* 2>/dev/null | head -1 || true)"
if [[ -z "$LATEST_BACKUP" ]]; then
  echo "restore-claude-config: $CONFIG missing and no backups found in $BACKUP_DIR -- nothing to restore." >&2
  exit 0
fi

echo "restore-claude-config: $CONFIG missing -- restoring from $LATEST_BACKUP"
cp "$LATEST_BACKUP" "$CONFIG"
