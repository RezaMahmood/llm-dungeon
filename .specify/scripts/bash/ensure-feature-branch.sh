#!/usr/bin/env bash
# Resolve the git branch AND worktree that should be active for the current feature.
#
# Read-only: reports whether the working tree is already positioned in the
# linked worktree that matches the active feature (.specify/feature.json /
# SPECIFY_FEATURE_DIRECTORY), where that worktree should live by convention
# (`{primary repo root}/.worktrees/{branch}`), and what state exists today
# (branch present locally/remotely, worktree already registered, or the
# branch checked out somewhere unexpected). Does not run `git checkout` or
# `git worktree add` itself -- callers decide whether and how to switch.

set -e

JSON_MODE=false
for arg in "$@"; do
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--json]"
            exit 0
            ;;
    esac
done

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

CURRENT_REPO_ROOT=$(get_repo_root) || exit 1

_paths_output=$(get_feature_paths --no-persist) || { echo "ERROR: Failed to resolve feature paths" >&2; exit 1; }
eval "$_paths_output"
unset _paths_output

TARGET_BRANCH=$(basename "${FEATURE_DIR%/}")
CURRENT_GIT_BRANCH=$(git -C "$CURRENT_REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

LOCAL_EXISTS=false
if git -C "$CURRENT_REPO_ROOT" show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
    LOCAL_EXISTS=true
fi

REMOTE_EXISTS=false
if git -C "$CURRENT_REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$TARGET_BRANCH"; then
    REMOTE_EXISTS=true
fi

ON_TARGET=false
if [ "$CURRENT_GIT_BRANCH" = "$TARGET_BRANCH" ]; then
    ON_TARGET=true
fi

# `--git-common-dir` always resolves to the *original* repo's `.git` directory,
# even from inside a linked worktree (whose own `.git` is just a pointer file).
# Its parent is therefore the one canonical primary worktree root, unlike
# `--show-toplevel`, which returns whichever worktree is current.
_common_dir=$(git -C "$CURRENT_REPO_ROOT" rev-parse --git-common-dir 2>/dev/null || echo ".git")
case "$_common_dir" in
    /*) _common_dir_abs="$_common_dir" ;;
    *) _common_dir_abs="$CURRENT_REPO_ROOT/$_common_dir" ;;
esac
PRIMARY_REPO_ROOT="$(CDPATH="" cd "$(dirname "$_common_dir_abs")" && pwd)"

WORKTREE_PATH="$PRIMARY_REPO_ROOT/.worktrees/$TARGET_BRANCH"

# Map TARGET_BRANCH -> its currently registered worktree path, if any.
EXISTING_PATH_FOR_BRANCH=""
_wt_path=""
while IFS= read -r _line; do
    case "$_line" in
        "worktree "*) _wt_path="${_line#worktree }" ;;
        "branch refs/heads/$TARGET_BRANCH")
            EXISTING_PATH_FOR_BRANCH="$_wt_path"
            ;;
        "") _wt_path="" ;;
    esac
done < <(git -C "$PRIMARY_REPO_ROOT" worktree list --porcelain 2>/dev/null)

WORKTREE_EXISTS_AT_TARGET_PATH=false
if [ -n "$EXISTING_PATH_FOR_BRANCH" ]; then
    _existing_resolved="$(CDPATH="" cd "$EXISTING_PATH_FOR_BRANCH" 2>/dev/null && pwd || echo "$EXISTING_PATH_FOR_BRANCH")"
    _target_resolved="$(CDPATH="" cd "$(dirname "$WORKTREE_PATH")" 2>/dev/null && pwd)/$(basename "$WORKTREE_PATH")"
    if [ "$_existing_resolved" = "$_target_resolved" ]; then
        WORKTREE_EXISTS_AT_TARGET_PATH=true
    fi
fi

BRANCH_CHECKED_OUT_ELSEWHERE=""
if [ -n "$EXISTING_PATH_FOR_BRANCH" ] && [ "$WORKTREE_EXISTS_AT_TARGET_PATH" = false ]; then
    BRANCH_CHECKED_OUT_ELSEWHERE="$EXISTING_PATH_FOR_BRANCH"
fi

PRIMARY_ROOT_CURRENT_BRANCH=$(git -C "$PRIMARY_REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

ON_TARGET_WORKTREE=false
_current_resolved="$(CDPATH="" cd "$CURRENT_REPO_ROOT" && pwd)"
_target_wt_resolved="$(CDPATH="" cd "$(dirname "$WORKTREE_PATH")" 2>/dev/null && pwd)/$(basename "$WORKTREE_PATH")"
if [ "$_current_resolved" = "$_target_wt_resolved" ]; then
    ON_TARGET_WORKTREE=true
fi

PRIMARY_ROOT_IS_ON_TARGET_BRANCH=false
if [ "$PRIMARY_ROOT_CURRENT_BRANCH" = "$TARGET_BRANCH" ] && [ "$BRANCH_CHECKED_OUT_ELSEWHERE" = "$PRIMARY_REPO_ROOT" ]; then
    PRIMARY_ROOT_IS_ON_TARGET_BRANCH=true
fi

if $JSON_MODE; then
    if has_jq; then
        jq -cn \
            --arg repo_root "$CURRENT_REPO_ROOT" \
            --arg primary_repo_root "$PRIMARY_REPO_ROOT" \
            --arg feature_dir "$FEATURE_DIR" \
            --arg target_branch "$TARGET_BRANCH" \
            --arg current_branch "$CURRENT_GIT_BRANCH" \
            --argjson on_target "$ON_TARGET" \
            --argjson local_exists "$LOCAL_EXISTS" \
            --argjson remote_exists "$REMOTE_EXISTS" \
            --arg worktree_path "$WORKTREE_PATH" \
            --argjson on_target_worktree "$ON_TARGET_WORKTREE" \
            --argjson worktree_exists_at_target_path "$WORKTREE_EXISTS_AT_TARGET_PATH" \
            --arg branch_checked_out_elsewhere "$BRANCH_CHECKED_OUT_ELSEWHERE" \
            --arg primary_root_current_branch "$PRIMARY_ROOT_CURRENT_BRANCH" \
            --argjson primary_root_is_on_target_branch "$PRIMARY_ROOT_IS_ON_TARGET_BRANCH" \
            '{REPO_ROOT:$repo_root,PRIMARY_REPO_ROOT:$primary_repo_root,FEATURE_DIR:$feature_dir,TARGET_BRANCH:$target_branch,CURRENT_BRANCH:$current_branch,ON_TARGET_BRANCH:$on_target,LOCAL_BRANCH_EXISTS:$local_exists,REMOTE_TRACKING_BRANCH_EXISTS:$remote_exists,WORKTREE_PATH:$worktree_path,ON_TARGET_WORKTREE:$on_target_worktree,WORKTREE_EXISTS_AT_TARGET_PATH:$worktree_exists_at_target_path,BRANCH_CHECKED_OUT_ELSEWHERE:$branch_checked_out_elsewhere,PRIMARY_ROOT_CURRENT_BRANCH:$primary_root_current_branch,PRIMARY_ROOT_IS_ON_TARGET_BRANCH:$primary_root_is_on_target_branch}'
    else
        printf '{"REPO_ROOT":"%s","PRIMARY_REPO_ROOT":"%s","FEATURE_DIR":"%s","TARGET_BRANCH":"%s","CURRENT_BRANCH":"%s","ON_TARGET_BRANCH":%s,"LOCAL_BRANCH_EXISTS":%s,"REMOTE_TRACKING_BRANCH_EXISTS":%s,"WORKTREE_PATH":"%s","ON_TARGET_WORKTREE":%s,"WORKTREE_EXISTS_AT_TARGET_PATH":%s,"BRANCH_CHECKED_OUT_ELSEWHERE":"%s","PRIMARY_ROOT_CURRENT_BRANCH":"%s","PRIMARY_ROOT_IS_ON_TARGET_BRANCH":%s}\n' \
            "$(json_escape "$CURRENT_REPO_ROOT")" "$(json_escape "$PRIMARY_REPO_ROOT")" "$(json_escape "$FEATURE_DIR")" "$(json_escape "$TARGET_BRANCH")" "$(json_escape "$CURRENT_GIT_BRANCH")" "$ON_TARGET" "$LOCAL_EXISTS" "$REMOTE_EXISTS" "$(json_escape "$WORKTREE_PATH")" "$ON_TARGET_WORKTREE" "$WORKTREE_EXISTS_AT_TARGET_PATH" "$(json_escape "$BRANCH_CHECKED_OUT_ELSEWHERE")" "$(json_escape "$PRIMARY_ROOT_CURRENT_BRANCH")" "$PRIMARY_ROOT_IS_ON_TARGET_BRANCH"
    fi
else
    echo "REPO_ROOT: $CURRENT_REPO_ROOT"
    echo "PRIMARY_REPO_ROOT: $PRIMARY_REPO_ROOT"
    echo "FEATURE_DIR: $FEATURE_DIR"
    echo "TARGET_BRANCH: $TARGET_BRANCH"
    echo "CURRENT_BRANCH: $CURRENT_GIT_BRANCH"
    echo "ON_TARGET_BRANCH: $ON_TARGET"
    echo "LOCAL_BRANCH_EXISTS: $LOCAL_EXISTS"
    echo "REMOTE_TRACKING_BRANCH_EXISTS: $REMOTE_EXISTS"
    echo "WORKTREE_PATH: $WORKTREE_PATH"
    echo "ON_TARGET_WORKTREE: $ON_TARGET_WORKTREE"
    echo "WORKTREE_EXISTS_AT_TARGET_PATH: $WORKTREE_EXISTS_AT_TARGET_PATH"
    echo "BRANCH_CHECKED_OUT_ELSEWHERE: $BRANCH_CHECKED_OUT_ELSEWHERE"
    echo "PRIMARY_ROOT_CURRENT_BRANCH: $PRIMARY_ROOT_CURRENT_BRANCH"
    echo "PRIMARY_ROOT_IS_ON_TARGET_BRANCH: $PRIMARY_ROOT_IS_ON_TARGET_BRANCH"
fi
