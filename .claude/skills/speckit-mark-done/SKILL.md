---
name: "speckit-mark-done"
description: "Check whether a spec's tasks are fully complete and rename its specs/ folder to append (or remove) a -done suffix accordingly, fix cross-references, then commit, push, open a PR, and clean up the working branch/worktree."
argument-hint: "[path to a specs/<feature> folder — omit to scan every spec]"
compatibility: "Requires spec-kit project structure with .specify/ directory and the gh CLI authenticated for PR creation"
metadata:
  author: "local"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

If non-empty, this names a single spec to check — either a bare feature folder name
(`005-story-publishing`), a `specs/`-relative path, or an absolute/relative filesystem path.
If empty, check every feature folder under `specs/`.

## Goal

Keep each feature's folder name under `specs/` an honest, self-updating signal of whether
that feature is fully built: append `-done` when every task in its `tasks.md` is checked
off, and strip `-done` back off the moment that stops being true (e.g. a bug fix or
clarification reopens work on an already-shipped spec). Whenever a folder is renamed, fix
every reference to the old path elsewhere in the repo so nothing links to a dead path, then
land the result as its own reviewed PR.

This mirrors what was done by hand in commit `d56dedd` ("chore(specs): mark fully-shipped
specs as done") — this skill exists to repeat that operation on demand instead of redoing it
manually each time specs cross the finish line (or fall back out of it).

## Key rules

- **Never edit on `main` directly.** All renames, reference fixes, and commits happen in a
  dedicated worktree/branch created for this run, per this project's standing rule to branch
  before any repo changes.
- **`tasks.md` is the sole source of truth for completion.** A spec is "done" only when its
  `tasks.md` exists, contains at least one task checkbox, and every checkbox is checked
  (`- [x]` or `- [X]`, any indentation). A spec with no `tasks.md`, or a `tasks.md` with zero
  checkbox lines, is **indeterminate** — never rename it in either direction, just note it as
  skipped.
- **Only touch feature folders.** Restrict scope to `specs/` entries matching `^[0-9]{3}-`
  (the spec-kit numbering convention) with an optional trailing `-done`. Leave
  `specs/designs/` and anything else alone.
- **Reference fixes exclude the renamed spec's own directory.** Historical self-references
  inside a spec's own `plan.md`/`tasks.md` (e.g. "Input: Design documents from
  `/specs/002-login-and-access-control/`") record what the artifact said at generation time
  and are left untouched — exactly as the precedent commit did. Only fix references to the
  folder that live in *other* files.
- **No-op means no branch.** If nothing needs to change, say so and stop — don't create a
  branch, worktree, commit, or PR for a clean run.
- **One PR per invocation.** If multiple specs need changes in the same run, batch them into
  a single branch/commit/PR, not one per spec.
- **Do not force anything.** If a git operation fails (dirty tree, existing branch/worktree,
  naming collision), stop and report — don't `--force`, `reset --hard`, or delete work to get
  unstuck.

## Execution Steps

### 1. Resolve the primary repo root

```bash
git rev-parse --is-inside-work-tree >/dev/null || { echo "Not a git repo"; exit 1; }
_common_dir=$(git rev-parse --git-common-dir)
case "$_common_dir" in /*) : ;; *) _common_dir="$(pwd)/$_common_dir" ;; esac
PRIMARY_REPO_ROOT="$(CDPATH= cd "$(dirname "$_common_dir")" && pwd)"
```

Using `--git-common-dir` (not `--show-toplevel`) means this resolves correctly even if
invoked from inside an existing feature worktree. All `specs/` scanning below reads from
`$PRIMARY_REPO_ROOT/specs` on the `main` tip currently checked out there (read-only — nothing
is written to `PRIMARY_REPO_ROOT` directly).

### 2. Build the scan list

- If `$ARGUMENTS` is empty: list every entry directly under `$PRIMARY_REPO_ROOT/specs`
  matching `^[0-9]{3}-.*$`.
- If `$ARGUMENTS` names one spec: normalize it to a bare folder name under `specs/` (strip
  any `specs/` prefix or absolute path, strip a trailing slash). If it doesn't exist under
  `specs/`, stop and report the miss, listing the available spec folder names so the user can
  correct it.

### 3. Evaluate each spec in scope (read-only)

For each folder name `N`:

- `base = N` with a trailing `-done` stripped if present; `currently_done = (N != base)`.
- `tasks_file = specs/$N/tasks.md`.
- If `tasks_file` doesn't exist → **indeterminate**, skip, note why.
- Else count checkbox lines:

  ```bash
  incomplete=$(grep -cE '^[[:space:]]*-[[:space:]]\[[[:space:]]\]' "$tasks_file")
  complete=$(grep -cE '^[[:space:]]*-[[:space:]]\[[xX]\]' "$tasks_file")
  total=$((incomplete + complete))
  ```

  - If `total == 0` → **indeterminate**, skip, note why.
  - `fully_done = (incomplete == 0)`.
- Decide the action for this spec:
  - `fully_done && !currently_done` → **rename to `$base-done`**.
  - `!fully_done && currently_done` → **rename to `$base`** (revert).
  - Otherwise → **no change**.

Collect the list of `(old_name → new_name)` pairs that need a rename. Also collect a summary
line per indeterminate/no-change spec for the final report.

### 4. Stop early if there's nothing to do

If the rename list is empty, report a one-line status per spec checked (done / not done /
indeterminate / already correct) and **stop here** — no branch, no commit, no PR.

### 5. Create a dedicated worktree and branch for the change

Pick a branch name:
- Exactly one rename → `chore/mark-<base>-done` (or `chore/reopen-<base>` if it's a revert).
- Multiple renames → `chore/spec-status-sync-<UTC timestamp, e.g. 20260829-173000>`.

```bash
WORKTREE_PATH="$PRIMARY_REPO_ROOT/.worktrees/$BRANCH"
git -C "$PRIMARY_REPO_ROOT" worktree add "$WORKTREE_PATH" -b "$BRANCH" main
cd "$WORKTREE_PATH"
```

If `worktree add` fails (branch name collision, dirty state, etc.), stop and report the exact
git error — do not force it. `main` itself is never checked out or modified by this step.

### 6. Apply the renames

From inside `$WORKTREE_PATH`, for each `(old → new)` pair:

```bash
git mv "specs/$old" "specs/$new"
```

If the destination already exists (collision), stop, leave that one pair out, report the
conflict, and continue with the rest.

### 7. Clean up the finished feature's own worktree pointer

For each `(old → new)` pair that is a **forward** rename (`base` → `base-done`, i.e. the
feature just became fully done — not a revert): if a worktree exists at
`$PRIMARY_REPO_ROOT/.worktrees/$base` (check with `git -C "$PRIMARY_REPO_ROOT" worktree list
--porcelain`), delete its `.specify/feature.json` if present:

```bash
rm -f "$PRIMARY_REPO_ROOT/.worktrees/$base/.specify/feature.json"
```

The feature is finished, so that per-checkout pointer no longer needs to resolve anything —
leaving it in place risks the same kind of staleness the `check-worktree-sync.sh` PreToolUse
hook exists to catch, if that worktree's branch is ever reused or checked out elsewhere later.
This is a plain file deletion outside `$WORKTREE_PATH` (the temporary worktree this run is
using for the rename/PR), not a git operation, and it does not touch or remove the feature's
worktree itself — per the Key Rules, worktree removal stays a separate, manual step for the
user to do once the feature's branch is merged. Skip silently if no such worktree exists (the
feature may never have had one, or it was already removed).

Also remove that worktree's devcontainer, if the per-worktree isolated-devcontainer workflow
(`bin/wt`, see `docs/WORKTREE_CONTAINER_WORKFLOW.md`) is in use — unlike the worktree itself,
the container holds no unique state worth keeping (it's cheaply recreated by `bin/wt` from the
shared cached image/volumes), so it's safe to fully remove rather than just stop:

```bash
CONTAINER_ID="$(docker ps -aq --filter "label=devcontainer.local_folder=$PRIMARY_REPO_ROOT/.worktrees/$base" 2>/dev/null || true)"
[ -n "$CONTAINER_ID" ] && docker rm -f "$CONTAINER_ID" >/dev/null
```

Skip silently if `docker` isn't available or no such container is found — the workflow may not
be in use for this repo/session.

### 8. Fix cross-references

For each `(old → new)` pair, find every file elsewhere in the repo that mentions the old
folder name and update it:

```bash
grep -rlF "$old" . \
  --exclude-dir=.git --exclude-dir=.worktrees --exclude-dir=node_modules \
  | grep -vF "specs/$new/" \
  | xargs -r sed -i "s/$old/$new/g"
```

(Substitute in the literal strings — spec folder names contain no regex metacharacters, but
still treat `grep -F`/plain substitution as authoritative over a hand-written regex.) The
`grep -vF "specs/$new/"` exclusion is what keeps the renamed spec's own files (already moved
to their new path in step 6) out of this pass, per the Key Rules note on historical
self-references.

This covers both bare mentions (`` `001-ci-cd-foundation` ``) and path mentions
(`specs/001-ci-cd-foundation/quickstart.md`) in one pass, since the latter contains the former
as a substring.

After running it for every pair, re-grep for each `old` name repo-wide (same excludes) to
confirm nothing outside the renamed spec's own directory still references it. Report any
survivors rather than silently leaving them.

### 9. Review and commit

```bash
git status
git diff --stat
```

Confirm the diff is exactly: the renamed directories (as renames, not add+delete, so history
is preserved) plus the reference-fixing edits. Then:

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(specs): <one line summarizing the rename(s)>

<one line per spec: what changed and why — fully checked off in tasks.md / tasks
reopened since being marked done>. Update cross-references to the renamed path(s)
in <list the files touched>.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

Model the message on `d56dedd`'s commit message.

### 10. Push and open a PR

```bash
git push -u origin "$BRANCH"
gh pr create --title "<same one-liner as the commit subject>" --label "AI Generated" --label "Claude" --body "$(cat <<'EOF'
## Summary
- <one bullet per spec renamed, old name -> new name, and why>

## Test plan
- [ ] Confirm no remaining links to the old path(s): `grep -rF "<old>" . --exclude-dir=.git --exclude-dir=.worktrees`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

If `AI Generated` and/or `Claude` labels don't exist in the repo, create the PR without
failing the run — retry `gh pr create` without `--label` rather than aborting.

Report the PR URL back to the user.

### 11. Clean up the working worktree and branch

```bash
cd "$PRIMARY_REPO_ROOT"
git worktree remove "$WORKTREE_PATH"
git branch -D "$BRANCH"
git worktree prune
```

`git branch -D` here only removes the **local** branch pointer now that its commit is pushed
and the PR is open against `origin/$BRANCH` — it does not touch the remote branch the PR
needs, and does not delete or close the PR. If `worktree remove` fails because something is
still using the path, stop and report rather than forcing removal.

## Done When

- [ ] Every spec in scope has been evaluated against its `tasks.md` completion state.
- [ ] Any folder whose name no longer matches its completion state has been renamed
      (`git mv`), preserving history.
- [ ] Every reference to a renamed folder elsewhere in the repo (outside the renamed spec's
      own directory) has been updated to the new path.
- [ ] For each spec newly marked done, `.specify/feature.json` has been removed from that
      feature's own worktree (`.worktrees/<base>`) if one exists — the worktree itself is left
      alone.
- [ ] For each spec newly marked done, that worktree's devcontainer (if the `bin/wt` workflow
      is in use) has been removed — skipped silently if `docker`/the container isn't present.
- [ ] If — and only if — a rename occurred: the change is committed, pushed, and a PR is
      open, and the temporary local worktree and branch used to produce it have been removed
      (leaving `main` untouched throughout and the remote PR branch intact).
- [ ] If no rename was needed: a status report was given and no branch/commit/PR was created.
