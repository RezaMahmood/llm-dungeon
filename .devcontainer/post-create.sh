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

# ---------------------------------------------------------------------------
# Local offline test harness (specs/027-local-offline-test-harness, FR-012).
#
# Everything below is installed at *build* time so a freshly created
# container can run the full local suite and the offline stack with no
# manual setup step (SC-007). Versions are pinned explicitly rather than
# floating, per the constitution's Dependency & Supply Chain requirement.
# ---------------------------------------------------------------------------

# Lifecycle commands run with the workspace folder as the working directory,
# but derive the root from this script's own location so the block below is
# also correct when it is run by hand (e.g. after editing it).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Python: production (infrastructure/terraform/terraform.tfvars,
# functions_python_version) and CI (.github/workflows/test.yml) both target
# 3.11, while this container's base image ships 3.14. The Azure Functions
# Python worker supports a fixed set of versions and 3.14 is not among them,
# so the real host cannot run here at all without a 3.11 interpreter --
# and pinning to the same minor CI and production pin means a version-
# specific failure is no longer invisible locally.
#
# The minor (not the patch) is pinned deliberately: '3.11' is exactly the
# granularity `python-version: '3.11'` in CI and `functions_python_version`
# in Terraform use, so pinning a patch here would make local *diverge* from
# the two environments this is meant to match.
PYTHON_VERSION="3.11"
VENV_DIR="$HOME/.venvs/llm-dungeon"

# Azure Functions Core Tools: GitHub release zip. The linux-arm64 asset is
# what this arm64 host needs; the x64 entry is kept so the container also
# builds on an Intel/AMD host. Checksums are the values published as the
# release's own `.zip.sha2` assets, committed here rather than fetched at
# install time -- fetching the checksum from the same origin as the archive
# verifies transport, not provenance. When bumping the version, take the new
# values from:
#   https://github.com/Azure/azure-functions-core-tools/releases/download/<ver>/Azure.Functions.Cli.linux-{arm64,x64}.<ver>.zip.sha2
FUNC_TOOLS_VERSION="4.14.0"
FUNC_TOOLS_SHA256_ARM64="c690bc66a82da1e75cfd20ceff73822f7ad06fd254608a1fe3669f2efc2c8dea"
FUNC_TOOLS_SHA256_X64="ecce0d57e288efc85d22cce7fc37d7129e78d0918368e8f1c84e9d3d354689aa"
FUNC_TOOLS_HOME="$HOME/.local/share/azure-functions-core-tools"

# npm globals. Azurite backs AzureWebJobsStorage for the Functions host; the
# SWA CLI is the local stack's entry point and is the only component that
# reads staticwebapp.config.json.
AZURITE_VERSION="3.37.0"
SWA_CLI_VERSION="2.0.10"

# Shared across every worktree container (named volume, see devcontainer.json)
# so the ~250MB Core Tools archive is downloaded once per host rather than
# once per worktree.
TOOL_CACHE_DIR="$HOME/.cache/llm-dungeon-tools"

install_python_toolchain() {
  # Creates a 3.11 virtualenv and installs the same requirement files CI
  # installs, so `pytest` works in a fresh container with no pip step.
  # devcontainer.json puts $VENV_DIR/bin ahead of the image's 3.14 on PATH,
  # which is what makes `python --version` report 3.11.x (SC-007).
  uv python install "$PYTHON_VERSION" \
    && uv venv --python "$PYTHON_VERSION" "$VENV_DIR" \
    && VIRTUAL_ENV="$VENV_DIR" uv pip install \
      -r "$REPO_ROOT/src/backend/requirements.txt" \
      -r "$REPO_ROOT/src/backend/requirements-dev.txt" \
      -r "$REPO_ROOT/infrastructure/tests/requirements.txt"
}

install_core_tools() {
  local arch asset expected zip dest
  case "$(uname -m)" in
    aarch64|arm64) arch="linux-arm64"; expected="$FUNC_TOOLS_SHA256_ARM64" ;;
    x86_64|amd64)  arch="linux-x64";   expected="$FUNC_TOOLS_SHA256_X64" ;;
    *) echo "Unsupported architecture for Core Tools: $(uname -m)" >&2; return 1 ;;
  esac

  asset="Azure.Functions.Cli.${arch}.${FUNC_TOOLS_VERSION}.zip"
  zip="$TOOL_CACHE_DIR/$asset"
  dest="$FUNC_TOOLS_HOME/$FUNC_TOOLS_VERSION"

  mkdir -p "$TOOL_CACHE_DIR" "$FUNC_TOOLS_HOME"

  # A cached archive from an earlier worktree's container is reused only if
  # it still matches the pinned checksum; anything else is re-downloaded.
  if ! echo "$expected  $zip" | sha256sum --check --status 2>/dev/null; then
    rm -f "$zip"
    # Download to a temp name and rename, so a container creating this file
    # concurrently with another worktree's never sees a half-written archive.
    curl -fsSL -o "$zip.$$.part" \
      "https://github.com/Azure/azure-functions-core-tools/releases/download/${FUNC_TOOLS_VERSION}/${asset}" \
      && mv -f "$zip.$$.part" "$zip"
  fi

  echo "$expected  $zip" | sha256sum --check --status || {
    echo "Core Tools checksum mismatch for $asset -- refusing to install." >&2
    rm -f "$zip"
    return 1
  }

  rm -rf "$dest"
  unzip -q "$zip" -d "$dest" \
    && chmod +x "$dest/func" \
    && ln -sfn "$dest/func" "$HOME/.local/bin/func"
  # `gozip` ships alongside `func` and is invoked by it when packaging; it
  # arrives without the executable bit, same as `func` itself.
  [[ -f "$dest/gozip" ]] && chmod +x "$dest/gozip"
  [[ -x "$HOME/.local/bin/func" ]]
}

install_node_clis() {
  # npm's global prefix under the node feature is group-writable by `vscode`,
  # so no sudo -- and no root-owned files in a user-owned tree.
  npm install --global --no-fund --no-audit \
    "azurite@${AZURITE_VERSION}" \
    "@azure/static-web-apps-cli@${SWA_CLI_VERSION}"
}

retry install_python_toolchain
retry install_core_tools
retry install_node_clis
