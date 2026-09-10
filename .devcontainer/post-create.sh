#!/usr/bin/env bash
# postCreateCommand for .devcontainer/devcontainer.json.
#
# Installs uv, then the Claude Code CLI (a standalone native binary, no
# Node dependency) so bin/wt can exec `claude` inside this container.
set -euo pipefail

# Docker creates a fresh named volume's mount point (and any missing parent
# directories, e.g. ~/.cache) as root before the container's entrypoint
# runs, even though this image's default user is `vscode` -- confirmed
# while building this config: the `claude` installer failed with `EACCES:
# permission denied, mkdir '/home/vscode/.cache/claude'` because
# ~/.cache itself was root-owned. Fix ownership of both cache-volume mount
# points up front; safe to rerun on an already-fixed tree.
sudo chown -R vscode:vscode /home/vscode/.cache /home/vscode/.terraform.d 2>/dev/null || true

# The devcontainer lifecycle runs postCreateCommand (this script) BEFORE
# postStartCommand (restore-claude-config.sh), so on a freshly created
# container ~/.claude.json does not exist yet when the installer below
# runs. The installer noticed and printed, twice, per creation:
#
#   Claude configuration file not found at: /home/vscode/.claude.json
#   A backup file exists at: /home/vscode/.claude/backups/.claude.json.backup.<ts>
#   You can manually restore it by running: cp "..." "/home/vscode/.claude.json"
#
# That advice is actively wrong here: ~/.claude/backups/ is the *host's*
# backup directory (it arrives through the shared ~/.claude bind mount), so
# following it would install a stale host config that postStartCommand
# overwrites seconds later anyway. Run the restore ourselves first instead
# -- it is idempotent and runs again on every later start.
RESTORE="$(dirname "${BASH_SOURCE[0]}")/restore-claude-config.sh"
[[ -x "$RESTORE" ]] && bash "$RESTORE" || true

# Both installers below place their binary in ~/.local/bin. That directory
# does not exist in the base image, and the Debian snippet in ~/.profile
# that would add it to PATH is conditional on the directory already
# existing (`if [ -d "$HOME/.local/bin" ]`) -- so at this point in a fresh
# container it is not on PATH, and the Claude installer ended every
# creation with a spurious "~/.local/bin is not in your PATH" setup
# warning. Creating it before installing satisfies the ~/.profile
# conditional for every later login shell (which is what `devcontainer
# exec` uses, and how bin/wt resolves `claude`); exporting it here makes
# this script's own PATH correct too, which is what silences the warning.
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

retry() {
  local attempts=3 delay=3 n=1
  until "$@"; do
    if (( n >= attempts )); then
      echo "Command failed after $attempts attempts: $*" >&2
      return 1
    fi
    echo "Retrying ($((n + 1))/$attempts) after failure: $*" >&2
    sleep "$delay"
    ((n++))
  done
}

install_uv() {
  # `retry` needs -e suspended around each attempt (see above), which means
  # a failing statement here would NOT abort the function early -- it would
  # fall through to the next line and the function's return status would be
  # whatever that last line returned (likely success), silently hiding the
  # real failure. Chaining with && makes the function's exit status
  # correctly reflect the first failing step.
  curl -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh \
    && sh /tmp/uv-install.sh \
    && rm -f /tmp/uv-install.sh
}

install_claude_code() {
  curl -fsSL https://claude.ai/install.sh -o /tmp/claude-install.sh \
    && bash /tmp/claude-install.sh \
    && rm -f /tmp/claude-install.sh
}

retry install_uv
retry install_claude_code
