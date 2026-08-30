#!/usr/bin/env bash
#
# cleanup-branches-worktrees.sh
#
# ─────────────────────────────────────────────────────────────────────────
# USE CASE
# ─────────────────────────────────────────────────────────────────────────
# This repo accumulates local git worktrees (see .worktrees/, created by the
# speckit-branch-ensure workflow) and local feature branches over the course
# of normal spec-kit / PR-driven development. Once a branch's PR is merged
# or closed on GitHub, the local branch and its worktree are dead weight:
# they clutter `git branch`/`git worktree list`, and stale worktree admin
# data can trip up other tooling (e.g. check-worktree-sync.sh).
#
# WHEN TO USE THIS
#   - Periodically (weekly, or whenever `git worktree list` /
#     `git branch` starts looking cluttered) to reclaim disk space and tidy
#     local state.
#   - After a batch of PRs have merged and you want to fast-forward your
#     local checkout back to a clean slate before starting new work.
#   - Before starting a new feature branch, to make sure a stale worktree
#     isn't left over from an earlier, already-merged feature with the same
#     branch-name pattern.
#
# WHEN NOT TO USE THIS
#   - Mid-feature, on a branch/worktree you're actively using — the script
#     always skips your current branch and the protected branches (main,
#     master, develop) so this is unlikely, but double-check the dry-run
#     output regardless.
#   - As a substitute for `git worktree prune` inside a script/hook that
#     needs a fast, non-interactive guarantee — this tool is interactive
#     cleanup for a human, not a CI primitive.
#
# WHAT IT DOES
#   1. `git fetch --prune origin` to sync remote-tracking refs (skip with
#      --no-fetch if you want a fully offline / no-network run).
#   2. For every local branch (except the current branch and protected
#      branches), determines whether it is safe to delete by checking, in
#      order of trust:
#        a. GitHub PR state via `gh pr list --head <branch>` (if the GitHub
#           CLI is installed and authenticated) — MERGED or CLOSED means
#           the branch's fate has already been decided on GitHub.
#        b. Whether the branch is an ancestor of origin/<default-branch>
#           (i.e. `git merge-base --is-ancestor`) — catches merges even
#           when `gh` isn't available.
#        c. Whether the remote-tracking branch has vanished (i.e. someone
#           deleted origin/<branch> after merging) as a last resort signal.
#      A branch with an OPEN PR is always kept. A branch with none of the
#      above signals is left for manual review (REVIEW bucket), never
#      auto-deleted, unless --force is passed.
#   3. Cross-references local worktrees (`git worktree list`) against the
#      branches above: any worktree whose branch is slated for deletion is
#      removed first (git worktree remove), then the branch is deleted
#      (git branch -D). Worktrees with uncommitted changes are always
#      skipped, even under --force.
#   4. Runs `git worktree prune` to clear stale worktree admin files for
#      directories that were already deleted outside of git (e.g. `rm -rf`).
#
# SAFETY MODEL
#   - Dry-run by default. Nothing is deleted unless you pass --yes.
#   - Branches with no GitHub confirmation and not merged into the default
#     branch are never deleted, even with --yes, unless you also pass
#     --force.
#   - Worktrees with uncommitted changes are never removed, with or
#     without --force.
#   - The current branch and protected branches (main, master, develop,
#     plus any passed via --protect) are never touched.
#
# USAGE
#   utilities/cleanup-branches-worktrees.sh [OPTIONS]
#
# OPTIONS
#   --yes, -y            Actually perform deletions (default: dry-run report only)
#   --force              Also delete branches with no GitHub/merge confirmation
#                         (the REVIEW bucket). Implies you've read the report.
#   --no-fetch            Skip `git fetch --prune origin` before analysis
#   --protect <branch>    Extra branch name to never delete (repeatable)
#   -h, --help             Show this help and exit
#
# EXAMPLES
#   utilities/cleanup-branches-worktrees.sh                # see what would happen
#   utilities/cleanup-branches-worktrees.sh --yes           # clean up safe branches/worktrees
#   utilities/cleanup-branches-worktrees.sh --yes --force    # also clear out REVIEW bucket
# ─────────────────────────────────────────────────────────────────────────

set -euo pipefail

DO_DELETE=false
FORCE_REVIEW=false
DO_FETCH=true
PROTECTED_BRANCHES=(main master develop)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)
      DO_DELETE=true
      shift
      ;;
    --force)
      FORCE_REVIEW=true
      shift
      ;;
    --no-fetch)
      DO_FETCH=false
      shift
      ;;
    --protect)
      PROTECTED_BRANCHES+=("$2")
      shift 2
      ;;
    -h|--help)
      sed -n '2,/^set -euo pipefail/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run with -h for usage." >&2
      exit 1
      ;;
  esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"

GH_AVAILABLE=false
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  GH_AVAILABLE=true
fi

if $DO_FETCH; then
  echo "Fetching and pruning origin..."
  git fetch --prune origin >/dev/null 2>&1 || echo "Warning: fetch failed, continuing with local state." >&2
fi

# Determine the default branch (origin/HEAD), falling back to "main".
DEFAULT_BRANCH="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="main"
fi

is_protected() {
  local branch="$1"
  for p in "${PROTECTED_BRANCHES[@]}"; do
    [[ "$branch" == "$p" ]] && return 0
  done
  return 1
}

# Returns one of: OPEN MERGED CLOSED NONE
pr_state_for() {
  local branch="$1"
  if ! $GH_AVAILABLE; then
    echo "NONE"
    return
  fi
  gh pr list --head "$branch" --state all --json state --jq '.[0].state // "NONE"' 2>/dev/null || echo "NONE"
}

is_merged_into_default() {
  local branch="$1"
  git merge-base --is-ancestor "$branch" "origin/$DEFAULT_BRANCH" 2>/dev/null
}

remote_branch_exists() {
  local branch="$1"
  git show-ref --verify --quiet "refs/remotes/origin/$branch"
}

declare -A BRANCH_DECISION   # branch -> DELETE / REVIEW / KEEP
declare -A BRANCH_REASON     # branch -> human-readable reason

mapfile -t LOCAL_BRANCHES < <(git for-each-ref --format='%(refname:short)' refs/heads)

for branch in "${LOCAL_BRANCHES[@]}"; do
  if [[ "$branch" == "$CURRENT_BRANCH" ]]; then
    BRANCH_DECISION["$branch"]="KEEP"
    BRANCH_REASON["$branch"]="currently checked out"
    continue
  fi
  if is_protected "$branch"; then
    BRANCH_DECISION["$branch"]="KEEP"
    BRANCH_REASON["$branch"]="protected branch"
    continue
  fi

  pr_state="$(pr_state_for "$branch")"

  if [[ "$pr_state" == "OPEN" ]]; then
    BRANCH_DECISION["$branch"]="KEEP"
    BRANCH_REASON["$branch"]="has an open PR on GitHub"
    continue
  fi

  if [[ "$pr_state" == "MERGED" ]]; then
    BRANCH_DECISION["$branch"]="DELETE"
    BRANCH_REASON["$branch"]="PR merged on GitHub"
    continue
  fi

  if [[ "$pr_state" == "CLOSED" ]]; then
    BRANCH_DECISION["$branch"]="DELETE"
    BRANCH_REASON["$branch"]="PR closed (without merge) on GitHub"
    continue
  fi

  # No PR signal from GitHub (or gh unavailable) — fall back to local git checks.
  if is_merged_into_default "$branch"; then
    BRANCH_DECISION["$branch"]="DELETE"
    BRANCH_REASON["$branch"]="merged into origin/$DEFAULT_BRANCH"
    continue
  fi

  if ! remote_branch_exists "$branch"; then
    BRANCH_DECISION["$branch"]="REVIEW"
    BRANCH_REASON["$branch"]="no remote branch and not merged — verify before deleting"
    continue
  fi

  BRANCH_DECISION["$branch"]="REVIEW"
  BRANCH_REASON["$branch"]="unmerged, no PR found — verify before deleting"
done

# ── Worktrees ───────────────────────────────────────────────────────────
declare -A WORKTREE_PATH_FOR_BRANCH
WT_PATH=""
WT_BRANCH=""
while IFS= read -r line; do
  if [[ "$line" == worktree\ * ]]; then
    WT_PATH="${line#worktree }"
    WT_BRANCH=""
  elif [[ "$line" == branch\ * ]]; then
    WT_BRANCH="${line#branch refs/heads/}"
    if [[ "$WT_PATH" != "$REPO_ROOT" && -n "$WT_BRANCH" ]]; then
      WORKTREE_PATH_FOR_BRANCH["$WT_BRANCH"]="$WT_PATH"
    fi
  fi
done < <(git worktree list --porcelain)

is_worktree_dirty() {
  local path="$1"
  [[ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ]]
}

echo ""
echo "== Branch report (default branch: $DEFAULT_BRANCH, GitHub checks: $($GH_AVAILABLE && echo enabled || echo unavailable)) =="
printf '%-40s %-8s %s\n' "BRANCH" "ACTION" "REASON"
for branch in "${LOCAL_BRANCHES[@]}"; do
  decision="${BRANCH_DECISION[$branch]}"
  reason="${BRANCH_REASON[$branch]}"
  wt_note=""
  if [[ -n "${WORKTREE_PATH_FOR_BRANCH[$branch]:-}" ]]; then
    wt_note=" [worktree: ${WORKTREE_PATH_FOR_BRANCH[$branch]}]"
  fi
  printf '%-40s %-8s %s%s\n' "$branch" "$decision" "$reason" "$wt_note"
done
echo ""

if ! $DO_DELETE; then
  echo "Dry run only — no changes made. Re-run with --yes to delete DELETE-bucket items."
  echo "REVIEW-bucket items are never deleted without --yes --force."
  git worktree prune --dry-run 2>/dev/null || true
  exit 0
fi

echo "Applying cleanup..."

for branch in "${LOCAL_BRANCHES[@]}"; do
  decision="${BRANCH_DECISION[$branch]}"
  if [[ "$decision" != "DELETE" ]] && ! { [[ "$decision" == "REVIEW" ]] && $FORCE_REVIEW; }; then
    continue
  fi

  wt_path="${WORKTREE_PATH_FOR_BRANCH[$branch]:-}"
  if [[ -n "$wt_path" ]]; then
    if is_worktree_dirty "$wt_path"; then
      echo "  SKIP  $branch — worktree at $wt_path has uncommitted changes"
      continue
    fi
    echo "  Removing worktree: $wt_path"
    git worktree remove "$wt_path"
  fi

  echo "  Deleting branch: $branch (${BRANCH_REASON[$branch]})"
  git branch -D "$branch"
done

echo "Pruning stale worktree admin data..."
git worktree prune -v

echo "Done."
