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
already positioned the session on the correct feature branch. Its
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

2. **Never sync on `main`/`master` as a side effect of this hook**: If the current branch is `main` or `master`, do not error; report `On {branch} — skipping automatic trunk sync (not a feature branch).` This hook only syncs feature branches; keeping `main` itself in sync is outside its scope.

3. **Check for uncommitted changes first**: Run `git status --porcelain`.
   - If it reports anything, **STOP**. Do not stash, commit, or discard anything on the user's behalf. Report the dirty files and ask the user to commit or stash before continuing.

4. **Fetch `origin/main`**: Run `git fetch origin main`.
   - If this fails (no `origin` remote, no network, or `main` doesn't exist on the remote), **STOP**. Show the exact git error and ask the user how to proceed — do not silently skip the sync.

5. **Bring `origin/main` into the current branch**: Run `git merge --ff-only origin/main` first.
   - **On success**: report the result in one line, e.g. `Synced \`{branch}\` with origin/main (now at {short SHA}).` or `Already up to date with origin/main.`, then let the calling command proceed.
   - **If a fast-forward isn't possible** (the branch has its own commits): run `git merge origin/main` to make an ordinary merge commit. Report what came in.
   - **If that merge conflicts**: resolve the conflicts here. Read both sides, keep the intent of each, and finish with `git add` + `git commit`. Report which files conflicted and how each was resolved. If a conflict genuinely cannot be resolved without a decision only the user can make (two incompatible intents, not a mechanical overlap), leave the merge in progress, explain the specific choice needed, and ask — do not abort silently and do not guess.

## Key rules

- Resolve conflicts; never erase them. `git merge` and a worked-through conflict resolution are expected. What stays prohibited is destroying a side to make the conflict disappear: no `--force`, no `git reset --hard`, no `git checkout --ours/--theirs` applied wholesale to dodge reading the diff, no auto-stash of the user's uncommitted work.
- Always syncs from `origin/main`, regardless of whether the current branch has its own upstream configured. A branch with no upstream is not a reason to skip — it is exactly the case this command exists to cover.
- Only ever advances the branch the session is already on, and never touches `main`/`master` itself.
- This hook syncs from the remote; it does not push. Pushing remains a separate, explicit step per the repo's git/PR workflow.

## Done When

- [ ] The current feature branch includes `origin/main`, by fast-forward or by a merge whose conflicts were resolved, **or**
- [ ] The hook determined there was nothing to do (already up to date, or on `main`/`master`), **or**
- [ ] The hook stopped and reported detached HEAD, dirty working-tree state, a fetch failure, or a conflict needing a decision only the user can make.
