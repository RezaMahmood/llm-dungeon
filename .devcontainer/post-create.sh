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
