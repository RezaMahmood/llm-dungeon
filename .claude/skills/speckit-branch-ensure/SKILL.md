---
name: "speckit-branch-ensure"
description: "Ensure the session is on the active feature's branch (creating it from main if needed) before spec-kit planning/task/clarify/analyze/implement commands run. Uses an existing worktree for that branch if there is one."
argument-hint: "(none — operates on the currently active feature)"
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "local"
  source: "local extension: branch-guard"
user-invocable: true
disable-model-invocation: false
---

## Purpose

This command is normally invoked **automatically** as a mandatory pre-hook
(`hooks.before_plan`, `hooks.before_tasks`, `hooks.before_clarify`,
`hooks.before_analyze`, `hooks.before_implement` in `.specify/extensions.yml`)
so that a feature's work lands on that feature's branch rather than on
whatever branch the session happened to start on. It can also be run manually
(`/speckit-branch-ensure`) at any time.

**The branch is what matters, not the directory.** A worktree is optional
(Constitution, Development Workflow & Quality Gates): if one already exists
for the feature's branch, this command moves the session there, because the
branch cannot be checked out twice. If there is no worktree, it simply
switches the current checkout onto the branch. It never creates a worktree.

It never touches `main`/`master` as a *target* branch, and never runs on
`/speckit-specify`, which creates the feature directory in the first place —
there is nothing to branch-match yet.

## Outline

1. **Resolve state**: Run `python3 .specify/scripts/python/ensure_feature_branch.py --json` from the current working directory. Parse the JSON for `REPO_ROOT`, `PRIMARY_REPO_ROOT`, `FEATURE_DIR`, `TARGET_BRANCH`, `CURRENT_BRANCH`, `ON_TARGET_BRANCH`, `LOCAL_BRANCH_EXISTS`, `REMOTE_TRACKING_BRANCH_EXISTS`, `WORKTREE_PATH`, `ON_TARGET_WORKTREE`, `WORKTREE_EXISTS_AT_TARGET_PATH`, `BRANCH_CHECKED_OUT_ELSEWHERE`. This script is read-only — it does not modify git state.

2. **Never touch main/master as a target**: If `TARGET_BRANCH` is `main` or `master`, stop and report the anomaly (no active feature to match) instead of acting.

3. **Already on the branch**: If `ON_TARGET_BRANCH` is `true`, report `Already on \`{TARGET_BRANCH}\`.` and go to step 7 — nothing to move.

4. **The branch is checked out in another worktree**: If `BRANCH_CHECKED_OUT_ELSEWHERE` is non-empty, `cd` there (a plain shell change of directory, not a git operation — it persists for the rest of this session's shell commands) and report the path. Git will not let the same branch be checked out twice, so this is the one case where the session has to move directories. Go to step 7.

5. **Protect uncommitted work before switching**: Run `git status --porcelain`. If anything is uncommitted, **STOP** and ask whether to commit or stash it. Do not stash, commit, or discard on the user's behalf, and do not switch branches over the top of it.

6. **Switch the current checkout onto the branch**:
   - If `LOCAL_BRANCH_EXISTS` is `true`: `git switch {TARGET_BRANCH}`
   - Else if `REMOTE_TRACKING_BRANCH_EXISTS` is `true`: `git switch -c {TARGET_BRANCH} origin/{TARGET_BRANCH}`
   - Else: `git switch -c {TARGET_BRANCH} main` (branch from `main` explicitly, never from whatever `HEAD` happens to be)

   On a git failure, **STOP**: show the exact error, say which branch you were trying to reach and why (feature `{FEATURE_DIR}` maps to branch `{TARGET_BRANCH}`), and ask how to proceed before the calling command continues.

7. **Bootstrap the local feature pointer**: `.specify/feature.json` is gitignored per-checkout local state (see `.specify/.gitignore`), so a checkout may have none, or a stale one from earlier work. Ensure the `.specify/feature.json` in the current working directory contains `{"feature_directory": "specs/{TARGET_BRANCH}"}` — write it if missing or different.

8. **On success**, report the outcome in one line, e.g. `Switched to \`{TARGET_BRANCH}\`.` or `Created \`{TARGET_BRANCH}\` from main.`, then let the calling command proceed.

## Key rules

- Never use `git checkout -f`, `git reset --hard`, `git stash`, or `git clean` to force a switch — surface the conflict to the user instead (step 5).
- Never switch onto or create a branch for `main` or `master` as a *target* — if `TARGET_BRANCH` ever resolves to one of those (e.g. no feature is active), stop and report the anomaly.
- New branches are created explicitly from `main`, not from "whatever `HEAD` currently points to".
- Do not create, move, or remove worktrees. This command uses one that already exists and otherwise works in the checkout it is in; `bin/wt` is the human entrypoint for creating one.

## Done When

- [ ] The session is on `TARGET_BRANCH` — in the current checkout, or in the existing worktree that already had it checked out — with `.specify/feature.json` pointing at `FEATURE_DIR`, **or**
- [ ] The command stopped and reported uncommitted work or a git error for the user to resolve.
