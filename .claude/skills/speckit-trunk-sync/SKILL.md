---
name: "speckit-trunk-sync"
description: "Sync the current feature branch with origin/main before any spec-kit planning or implementation command runs."
argument-hint: "(none — operates on the current branch)"
compatibility: "Requires a git repository"
metadata:
  author: "local"
  source: "local extension: git-sync"
user-invocable: true
disable-model-invocation: false
---

## Purpose

This command is normally invoked **automatically** as a mandatory pre-hook
(`hooks.before_plan`, `hooks.before_tasks`, `hooks.before_clarify`,
`hooks.before_analyze`, and `hooks.before_implement` in
`.specify/extensions.yml`), running *after* `speckit-branch-ensure` has
already positioned the session on the correct feature worktree/branch. Its
job is to bring `origin/main` into that branch before any spec-related work
(planning included, not implementation alone) starts, per Constitution
Principle XIII's sync-before-work rule — so a plan, task list, or
implementation is never written against a stale or diverged tree.

It syncs from `origin/main` specifically, not from the branch's own
upstream: a feature branch can be fully up to date with
`origin/{branch}` while being many commits behind `origin/main`, and a
branch that has never been pushed has no upstream at all but still needs
`origin/main` merged in. Checking the branch's own upstream would miss
both cases, so this command ignores it entirely.

It can also be run manually (`/speckit-trunk-sync`) at any time.

## Outline

1. **Resolve current branch**: Run `git rev-parse --abbrev-ref HEAD` from the current working directory.
   - If this reports `HEAD` (detached HEAD, not a branch — e.g. a manual mid-rebase or checked-out-tag state), **STOP**. Report that there is no branch to sync and ask the user to check out a branch first; do not attempt a merge with nothing to advance.

2. **Never sync on `main`/`master` as a target**: If the current branch is `main` or `master`, take no action, and report `On {branch} — not a feature branch, so there is nothing to sync here.` This hook only syncs feature branches; keeping `main` itself in sync is outside its scope. (When run automatically as a pre-hook this is a routine no-op; when run manually via `/speckit-trunk-sync` it is simply the answer to the sync request.)

3. **Check for uncommitted changes first**: Run `git status --porcelain`.
   - If it reports anything, **STOP**. Do not stash, commit, or discard anything on the user's behalf. Report the dirty files and ask the user to commit or stash before continuing.

4. **Fetch `origin/main`**: Run `git fetch origin main`.
   - If this fails (no `origin` remote, no network, or `main` doesn't exist on the remote), **STOP**. Show the exact git error and ask the user how to proceed — do not silently skip the sync.

5. **Fast-forward the current branch to include `origin/main`**: Run `git merge --ff-only origin/main`.
   - **On success**: report the result in one line, e.g. `Synced \`{branch}\` with origin/main (now at {short SHA}).` or `Already up to date with origin/main.`, then let the calling command proceed.
   - **On failure** (the branch has local commits that diverge from `origin/main`, so a fast-forward isn't possible): **STOP**. Do not run `git merge` without `--ff-only`, `git rebase`, `git reset --hard`, or `--force` anything — a divergence is reported, never worked around. Show the exact git error and the commits unique to each side (e.g. `git log --oneline origin/main..HEAD` and `git log --oneline HEAD..origin/main`), and ask the user how they want to reconcile the branches before the calling command continues.

## Key rules

- Never force anything: no `--force`, no `git reset --hard`, no auto-stash, no auto-merge-commit, no rebase. Any conflict or divergence is surfaced to the user, not resolved automatically — this satisfies the constitution's requirement that a divergence be "resolved or reported rather than worked around."
- Always syncs from `origin/main`, regardless of whether the current branch has its own upstream configured. A branch with no upstream is not a reason to skip — it is exactly the case this command exists to cover.
- Only ever fast-forwards the branch the session is already on — never fetches or switches to a different branch, and never touches `main`/`master` itself.
- This hook syncs from the remote; it does not push. Pushing remains a separate, explicit step per the repo's git/PR workflow.

## Done When

- [ ] The current feature branch is fast-forwarded to include `origin/main`, **or**
- [ ] The hook determined there was nothing to do (already up to date, or on `main`/`master`), **or**
- [ ] The hook stopped and reported detached HEAD, dirty working-tree state, a fetch failure, or a non-fast-forward divergence for the user to resolve.
