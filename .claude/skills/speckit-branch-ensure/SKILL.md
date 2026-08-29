---
name: "speckit-branch-ensure"
description: "Ensure a dedicated git worktree for the active feature's branch exists and that the session is positioned inside it (creating both if needed) before spec-kit planning/task/clarify/analyze/implement commands run."
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
so that each spec-kit feature is worked on in its own **git worktree** —
a separate working-tree directory sharing the same `.git`, checked out to
that feature's branch — so multiple features (and multiple concurrent
sessions) can be in progress at once without one session's branch switch
ever touching another session's files. It can also be run manually
(`/speckit-branch-ensure`) at any time.

Convention: every feature's worktree lives at
`{primary repo root}/.worktrees/{branch}`, where the "primary repo root" is
the one canonical checkout every worktree shares (resolved via
`git rev-parse --git-common-dir`, not `--show-toplevel`, so this still
resolves correctly when invoked from inside an existing worktree rather
than the primary one). The primary root itself is expected to stay on
`main` — feature work never happens there once a worktree exists for it.

It never touches `main`/`master` as a *target* branch, and never runs on
`/speckit-specify`, which creates the feature directory in the first place —
there is nothing to branch-match yet.

## Outline

1. **Resolve state**: Run `python3 .specify/scripts/python/ensure_feature_branch.py --json` from the current working directory. Parse the JSON for `REPO_ROOT` (repo root as seen from *here*, right now), `PRIMARY_REPO_ROOT`, `FEATURE_DIR`, `TARGET_BRANCH`, `CURRENT_BRANCH`, `ON_TARGET_BRANCH`, `LOCAL_BRANCH_EXISTS`, `REMOTE_TRACKING_BRANCH_EXISTS`, `WORKTREE_PATH`, `ON_TARGET_WORKTREE`, `WORKTREE_EXISTS_AT_TARGET_PATH`, `BRANCH_CHECKED_OUT_ELSEWHERE`, `PRIMARY_ROOT_CURRENT_BRANCH`, `PRIMARY_ROOT_IS_ON_TARGET_BRANCH`. This script is read-only — it does not modify git state.

2. **Never touch main/master as a target**: If `TARGET_BRANCH` is `main` or `master`, stop and report the anomaly (no active feature to match) instead of acting.

3. **Already positioned correctly**: If `ON_TARGET_WORKTREE` is `true`, report `Already in feature worktree at \`{WORKTREE_PATH}\` on branch \`{TARGET_BRANCH}\`.` and stop — nothing else to do.

4. **Worktree already exists at the conventional path**: If `WORKTREE_EXISTS_AT_TARGET_PATH` is `true` but step 3 didn't already match (i.e. the session's cwd isn't inside it yet), just switch there: run `cd {WORKTREE_PATH}` (a plain shell change of directory, not a git operation — persists for the rest of this session's shell commands). Skip to step 8.

5. **The feature's branch is checked out somewhere unexpected**: If `BRANCH_CHECKED_OUT_ELSEWHERE` is non-empty:
   - **If it equals `PRIMARY_REPO_ROOT`** (the primary checkout itself is sitting on this feature branch — a legacy/pre-worktree state): first move the primary checkout back to `main` with `git -C {PRIMARY_REPO_ROOT} checkout main`. If that fails (uncommitted changes would conflict), **STOP** per step 7's failure handling — do not force it. On success, create the worktree: `git -C {PRIMARY_REPO_ROOT} worktree add {WORKTREE_PATH} {TARGET_BRANCH}`, then `cd {WORKTREE_PATH}`. Continue to step 6.
   - **Otherwise** (checked out at some other, non-conventional path — e.g. a manually created worktree): **STOP**. Report the path found and ask the user whether to adopt that existing path (and treat it as this feature's worktree going forward) or remove it so a fresh one can be created at the conventional path. Do not move or delete another worktree yourself.

6. **No worktree exists yet for this branch**: Otherwise (branch isn't checked out anywhere as a worktree):
   - If `LOCAL_BRANCH_EXISTS` is `true`: `git -C {PRIMARY_REPO_ROOT} worktree add {WORKTREE_PATH} {TARGET_BRANCH}`
   - Else if `REMOTE_TRACKING_BRANCH_EXISTS` is `true`: `git -C {PRIMARY_REPO_ROOT} worktree add {WORKTREE_PATH} -b {TARGET_BRANCH} origin/{TARGET_BRANCH}`
   - Else: `git -C {PRIMARY_REPO_ROOT} worktree add {WORKTREE_PATH} -b {TARGET_BRANCH} main` (branch from `main` explicitly — see Key Rules on why this changed from "whatever HEAD happens to be")

   Then `cd {WORKTREE_PATH}`.

7. **On any git failure** in steps 5–6 (e.g. `checkout`/`worktree add` refuses because of uncommitted local changes, or the target path already exists and isn't empty): **STOP**. Do not stash, commit, discard, `worktree remove --force`, or otherwise force anything on the user's behalf. Show the exact git error, explain which worktree/branch you were trying to reach and why (feature `{FEATURE_DIR}` maps to branch `{TARGET_BRANCH}` at `{WORKTREE_PATH}`), and ask the user how to proceed before the calling spec-kit command continues.

8. **Bootstrap the worktree's local feature pointer**: `.specify/feature.json` is gitignored per-checkout local state (see `.specify/.gitignore`), so a freshly created worktree starts without one and would otherwise fail to self-resolve if a later command runs there without `SPECIFY_FEATURE_DIRECTORY` set. Once positioned in `{WORKTREE_PATH}` (whether just created or already existing), ensure `.specify/feature.json` there contains `{"feature_directory": "specs/{TARGET_BRANCH}"}` — write it if missing or different from that.

9. **On success**, report the outcome in one line, e.g. `Switched to feature worktree at \`{WORKTREE_PATH}\`.` or `Created feature worktree at \`{WORKTREE_PATH}\` (branch \`{TARGET_BRANCH}\`).`, then let the calling command proceed. All of this session's subsequent shell commands now run from `{WORKTREE_PATH}` by default (the shell's working directory persists across tool calls), and every `.specify/scripts/*` invocation from here on should keep using **relative** paths (e.g. `python3 .specify/scripts/python/...`) so resolution stays anchored to this worktree rather than accidentally reaching back to `PRIMARY_REPO_ROOT`.

## Key rules

- Never use `git checkout -f`, `git reset --hard`, `git stash`, `git clean`, or `git worktree remove --force` to force a switch — surface conflicts to the user instead (see step 7).
- Never switch onto or create a worktree for `main` or `master` as a *target* — if `TARGET_BRANCH` ever resolves to one of those (e.g. no feature is active), stop and report the anomaly instead of acting. The primary checkout moving *back to* `main` (step 5's legacy-migration case) is the one exception, since that's restoring the primary root to its expected resting state, not treating `main` as a feature.
- New branches are created explicitly from `main`, not "whatever `HEAD` currently points to" (a change from this hook's pre-worktree behavior). With multiple worktrees potentially checked out to different branches at once, "current HEAD" no longer reliably means "the trunk" — `main` is the one stable, unambiguous base to fork from.
- Do not delete, move, or `git worktree remove` a worktree that isn't the one this run is trying to create or enter — another feature's (or another session's) worktree is not this hook's to touch.
- This hook only creates/enters worktrees; it does not prune stale ones after a feature branch is merged. Removing a finished feature's worktree (`git worktree remove {path}` once its branch is merged and no session needs it) is a separate, manual cleanup step, not automated here.

## Done When

- [ ] The session's current working directory is `{WORKTREE_PATH}`, checked out to `TARGET_BRANCH`, with `.specify/feature.json` pointing at `FEATURE_DIR` (either it already was, or the hook created/switched to it), **or**
- [ ] The hook stopped and reported a blocking git error, or an unexpected-existing-worktree conflict, for the user to resolve.
