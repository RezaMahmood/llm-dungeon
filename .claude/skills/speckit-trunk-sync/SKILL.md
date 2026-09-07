---
name: "speckit-git-pull"
description: "Fast-forward the current feature branch from its remote tracking branch before implementation begins."
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
(`hooks.before_implement` in `.specify/extensions.yml`), running *after*
`speckit-branch-ensure` has already positioned the session on the correct
feature worktree/branch. Its only job is to make sure that branch is
up to date with its remote before implementation starts, so work doesn't
proceed against stale code or silently diverge from what's already merged.

It can also be run manually (`/speckit-git-pull`) at any time.

## Outline

1. **Resolve current branch**: Run `git rev-parse --abbrev-ref HEAD` from the current working directory.

2. **Never pull on `main`/`master` as a side effect of this hook**: If the current branch is `main` or `master`, skip silently and report `On {branch} — skipping automatic pull (not a feature branch).` This hook only syncs feature branches; keeping `main` in sync is outside its scope.

3. **Check for an upstream**: Run `git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null`.
   - If this fails (no upstream configured — e.g. a brand-new local branch that hasn't been pushed yet), skip silently and report `Branch \`{branch}\` has no upstream yet — nothing to pull.`

4. **Check for uncommitted changes**: Run `git status --porcelain`.
   - If it reports anything, **STOP**. Do not stash, commit, or discard anything on the user's behalf. Report the dirty files and ask the user to commit or stash before continuing.

5. **Fast-forward only**: Run `git pull --ff-only`.
   - **On success**: report the result in one line, e.g. `Pulled latest for \`{branch}\` (now at {short SHA}).` or `Already up to date.`, then let the calling command proceed.
   - **On failure** (diverged history, merge conflict, or anything else non-fast-forward): **STOP**. Do not run `git merge`, `git rebase`, `git reset --hard`, or `--force` anything. Show the exact git error and ask the user how they want to reconcile the branches before implementation continues.

## Key rules

- Never force anything: no `--force`, no `git reset --hard`, no auto-stash, no auto-merge/rebase. Any conflict or divergence is surfaced to the user, not resolved automatically.
- Only ever pulls the branch the session is already on — never fetches or switches to a different branch, and never touches `main`/`master`.
- This hook syncs from the remote; it does not push. Pushing remains a separate, explicit step per the repo's git/PR workflow.

## Done When

- [ ] The current feature branch is fast-forwarded to match its remote tracking branch, **or**
- [ ] The hook determined there was nothing to do (no upstream, already up to date, or on `main`/`master`), **or**
- [ ] The hook stopped and reported dirty working-tree state or a non-fast-forward divergence for the user to resolve.
