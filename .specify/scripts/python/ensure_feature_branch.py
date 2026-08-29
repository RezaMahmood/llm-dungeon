#!/usr/bin/env python3
"""Resolve the git branch AND worktree that should be active for the current feature.

Read-only: reports whether the working tree is already positioned in the
linked worktree that matches the active feature (.specify/feature.json /
SPECIFY_FEATURE_DIRECTORY), where that worktree should live by convention
(`{primary repo root}/.worktrees/{branch}`), and what state exists today
(branch present locally/remotely, worktree already registered, or the
branch checked out somewhere unexpected). Does not run `git checkout` or
`git worktree add` itself -- callers (e.g. the speckit-branch-ensure skill)
decide whether and how to switch.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    from common import get_feature_paths
except ImportError:  # pragma: no cover - direct execution from unusual cwd
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import get_feature_paths


HELP_TEXT = """Usage: ensure_feature_branch.py [OPTIONS]

Resolve the git branch and worktree that should be active for the current
feature and report whether the working tree is already positioned there.
Read-only.

OPTIONS:
  --json      Output in JSON format
  --help, -h  Show this help message
"""


def _git_ok(repo_root: Path, *args: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _git_output(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _primary_repo_root(current_repo_root: Path) -> Path:
    """The one canonical repo root shared by every worktree.

    `git rev-parse --git-common-dir` always resolves to the *original*
    repo's `.git` directory, even when run from inside a linked worktree
    (whose own `.git` is just a file pointing back at it). Its parent is
    therefore the primary worktree's root, regardless of which worktree
    this script is actually invoked from -- unlike `--show-toplevel`,
    which returns whichever worktree is current.
    """
    common_dir = _git_output(current_repo_root, "rev-parse", "--git-common-dir")
    if not common_dir:
        return current_repo_root
    resolved = (current_repo_root / common_dir).resolve()
    return resolved.parent


def _worktree_branch_map(primary_repo_root: Path) -> dict[str, str]:
    """Map branch name -> worktree path, from `git worktree list --porcelain`."""
    output = _git_output(primary_repo_root, "worktree", "list", "--porcelain")
    mapping: dict[str, str] = {}
    current_path: str | None = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            current_path = line[len("worktree "):].strip()
        elif line.startswith("branch ") and current_path is not None:
            ref = line[len("branch "):].strip()
            branch = ref.removeprefix("refs/heads/")
            mapping[branch] = current_path
            current_path = None
        elif line == "":
            current_path = None
    return mapping


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        sys.stdout.write(HELP_TEXT)
        return 0
    json_mode = "--json" in argv

    paths = get_feature_paths(no_persist=True, script_file=Path(__file__))
    current_repo_root = paths.repo_root
    target_branch = Path(str(paths.feature_dir).rstrip("/\\")).name

    current_branch = _git_output(current_repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    local_exists = _git_ok(
        current_repo_root, "show-ref", "--verify", "--quiet", f"refs/heads/{target_branch}"
    )
    remote_exists = _git_ok(
        current_repo_root,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/remotes/origin/{target_branch}",
    )

    primary_repo_root = _primary_repo_root(current_repo_root)
    worktree_path = primary_repo_root / ".worktrees" / target_branch
    branch_worktrees = _worktree_branch_map(primary_repo_root)
    existing_path_for_branch = branch_worktrees.get(target_branch, "")
    primary_root_current_branch = _git_output(primary_repo_root, "rev-parse", "--abbrev-ref", "HEAD")

    worktree_exists_at_target_path = (
        existing_path_for_branch != ""
        and Path(existing_path_for_branch).resolve() == worktree_path.resolve()
    )
    branch_checked_out_elsewhere = (
        existing_path_for_branch
        if existing_path_for_branch and not worktree_exists_at_target_path
        else ""
    )
    on_target_worktree = current_repo_root.resolve() == worktree_path.resolve()

    payload = {
        "REPO_ROOT": str(current_repo_root),
        "PRIMARY_REPO_ROOT": str(primary_repo_root),
        "FEATURE_DIR": str(paths.feature_dir),
        "TARGET_BRANCH": target_branch,
        "CURRENT_BRANCH": current_branch,
        "ON_TARGET_BRANCH": current_branch == target_branch,
        "LOCAL_BRANCH_EXISTS": local_exists,
        "REMOTE_TRACKING_BRANCH_EXISTS": remote_exists,
        "WORKTREE_PATH": str(worktree_path),
        "ON_TARGET_WORKTREE": on_target_worktree,
        "WORKTREE_EXISTS_AT_TARGET_PATH": worktree_exists_at_target_path,
        "BRANCH_CHECKED_OUT_ELSEWHERE": branch_checked_out_elsewhere,
        "PRIMARY_ROOT_CURRENT_BRANCH": primary_root_current_branch,
        "PRIMARY_ROOT_IS_ON_TARGET_BRANCH": (
            primary_root_current_branch == target_branch
            and branch_checked_out_elsewhere == str(primary_repo_root)
        ),
    }

    if json_mode:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
