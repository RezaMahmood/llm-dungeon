# CLAUDE.md

Operational instructions for Claude Code sessions in this repo: how
Claude works here, and what it must and must not do on GitHub.

This file binds Claude only. It states no rule for the repository or for
anyone else working in it, and it is not the authority on either: where
it contradicts the project's own governing documents, this file is wrong
and MUST be corrected, not worked around.

## Where the work happens

One piece of work at a time, anywhere in the repo. There is no session
isolation rule: Claude may move around the checkout, switch branches, and
sync with `main` as the work requires.

- **Branch first; never commit to `main`.** If the session starts on
  `main`, cutting the task's branch is its first act. `main` itself is
  only ever a base to branch from and a ref to sync against.
- **Navigate freely, deliberately.** `git checkout`, `git switch`,
  `git branch` and `git worktree` are all permitted. Before switching
  away from a branch, check `git status` and commit or stash anything
  uncommitted rather than carrying it across or losing it. Say which
  branch you moved to and why.
- **Sync with `main` and resolve conflicts locally.** `git fetch`,
  `git pull --ff-only`, and merging or rebasing `origin/main` into the
  task's branch are normal, expected acts — do them when the branch is
  behind, and resolve any conflict here rather than deferring it to
  GitHub. Resolve by understanding both sides; never discard a side to
  make the conflict go away, and never force-push over someone's work.
  `speckit-trunk-sync` remains the scripted path for spec-kit commands.
- **Worktrees, containers and directories are all optional.** Work in the
  primary checkout, in a git worktree, or in a devcontainer — whichever
  the user set up. No branch type requires any of them, and nothing is
  off-limits to read or edit. `bin/wt` is a human entrypoint Claude MUST
  NOT invoke, because it execs a new `claude` session; `bin/wt-sync` and
  a bare `bin/wt-prune` only report, and Claude MAY run them.
  `bin/wt-prune --yes` deletes branches and worktrees, so run it only
  when the user asks for that run.
- **Run tests, linters and builds where the toolchain is.** If a
  devcontainer is running for this checkout, prefix the command to
  execute in it (e.g.
  `devcontainer exec --workspace-folder . -- <command>`). If none is,
  running on the host is fine — say which you did.

## Git / PR workflow

Claude does local development and spec work — including resolving a
GitHub issue end to end — then pushes the branch and opens the pull
request itself. The GitHub-side pass is Claude Code's `/code-review`
skill, triggered explicitly, never automatically on push; it posts
findings as recommendations, gives no approving review and performs no
merge. **The requesting user reviews the findings and the required status
checks, then merges manually.**

- **Push.** When the work is ready, stage it, commit, and push the
  current branch with `git push origin HEAD` — never a different branch.
  First check any PR already associated with that branch
  (`gh pr view <branch> --json state`). Claude MUST NEVER push to the
  branch of a PR that is already merged or closed, even though the push
  would succeed: that work would land without anyone being asked to
  review it. Branch off current `main` and open a new PR instead.
  Pushing to a branch whose PR is still open is fine, and is the normal
  way to address review feedback.
- **Open the PR** immediately after pushing, with
  `gh pr create --label "AI Generated" --label "Claude" ...` (both labels
  already exist), a title per *PR title format* and a body per *PR
  description*.
- **Never merge a PR** — not with `gh pr merge`, not by enabling
  auto-merge, not through the API (`gh api --method PUT .../merge`, a
  `mergePullRequest` mutation). `.claude/settings.json` denies the
  `gh pr merge` forms; the API paths are governed by this rule alone.
- **Never monitor a PR to completion.** Report the checks' state once and
  hand back.
- **Close an issue** with `gh issue close` only when **both** hold: the
  user asked Claude to close that issue, and Claude verified the
  resolving work is merged to `origin/main` — not merely on a local
  branch, in a worktree, or in an open PR. Say what was verified. Never
  close an issue on Claude's own initiative; if either condition fails,
  leave it open and say why.

## PR description

A PR description is the only account of the change that survives to
`main`. Every PR Claude opens MUST state, proportionate to the change:

1. **What this is** — the issue or part it belongs to (`Part (c) of
   #293`). Use `Closes #NNN` only when the PR fully resolves that issue
   **and** the user asked for it to close.
2. **The problem** — the behaviour or evidence that motivated the change,
   not a restatement of the diff.
3. **What changed** — the decisions taken and why one option won. The
   file list is already in the diff; do not repeat it as prose.
4. **Testing** — what was actually run and what it actually returned.
   Anything not verified MUST be named as unverified.
5. **Known limits / follow-ups** — what was deliberately left undone, and
   why.
6. **Recommended review tier** — per *Code review triage*, with the
   reason it applies.

A one-line docs fix does not need six headings, but items 1, 4 and 5 are
never optional. A description MUST NOT link to the Claude Code
session/transcript; contain PII — reference records indirectly; claim a check passed that Claude did not observe pass, or
quote numbers it did not measure; or assert an approving review or ask
the user to merge. End it with the attribution footer:
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## PR title format

This repo merges exclusively by squash, so the PR title — not any commit
message — becomes the sole commit on `main` and is what `semantic-release`
reads to compute the next version. Every title MUST be Conventional
Commits, `type(scope): description` (or `type(scope)!:` for a breaking
change), and MUST pass the required `check-title` check
(`.github/workflows/pr-title-check.yml`).

- **`type`:** `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`,
  `build`, `ci`, `style`, `revert`.
- **`scope`, required on every title:** `frontend`, `backend`, `infra`,
  `ci`, `specs`, `deps`, `deps-dev`, `docs`. `scripts/pr-title-config.js`
  is the single source of truth (mirrored into the workflow) — check
  there rather than inventing a scope. Repo tooling and config
  (`.claude/`, `.specify/`, hooks) is `infra`.
- `feat(backend|frontend)` → minor bump; `fix`/`perf(backend|frontend)` →
  patch; `!` after the scope, or a `BREAKING CHANGE:` footer → major. The
  scope is descriptive only: releases are additionally gated by path-diff
  filtering, so `feat(backend)` cuts no release if no backend paths
  changed.

## Code review triage

Match the tier to the change rather than defaulting to either extreme.
`/code-review` runs locally at the level last used; `/code-review ultra
<PR#>` runs a multi-agent cloud review and is billed per run. Claude MAY
run the local tiers itself, names the resulting tier in the PR
description, and MUST NOT attempt to launch `ultra` — it is
user-triggered and billed, so ask the user to run it.

**Start from the diff:**

| The change | Minimum tier |
|---|---|
| Docs, comments or spec prose — nothing executable | none |
| ≤ ~150 changed lines, one component, covered by tests that ran green | `/code-review` |
| > ~150 lines, or 3+ components, or a new module or dependency | `/code-review high` |
| Anything in the blast-radius list below | `/code-review ultra <PR#>` |

**Blast radius — always `ultra`, whatever the diff size:**

- authentication, secrets, or permissions, including
  `.claude/settings*.json`, the hook scripts and `bin/`;
- CI/CD workflows, deployment, or infrastructure/Terraform;
- governance: `.specify/memory/`, this file, `CONTRIBUTING.md`;
- persisted data: schema, migrations, or anything that can delete or
  rewrite existing records;
- release machinery: `scripts/pr-title-config.js`, `.releaserc.json`.

**Then adjust for how the change was authored:**

- Opus-class model with the relevant tests run green — tier as the table
  says;
- smaller/faster model, or a long unattended run nobody watched — **one
  tier up**;
- mechanical and independently verified (a rename with a green build, a
  revert of an already-reviewed commit, a dependency bump with a passing
  suite) — **one tier down**, never below `none`.

Where two rows apply, the **highest** tier wins.

## Responding to code-review findings

When the user hands Claude a review (or a single finding) on one of
Claude's PRs and Claude fixes the underlying issue and pushes:

- **Inline review comment** — reply on that thread, not the PR generally,
  summarising the fix and the commit it landed in
  (`gh api repos/{owner}/{repo}/pulls/{pr}/comments -f body="..." -f in_reply_to={comment_id}`),
  then resolve it with the GraphQL `resolveReviewThread` mutation (look
  the thread id up with a `reviewThreads` query if only the comment
  id/URL is known).
- **Single posted comment** — reply as a normal PR comment, same content.
- **No fix warranted** (out of scope, handled elsewhere) — reply
  explaining why instead of silently resolving, and leave it to the user.

Resolving a thread is addressing feedback on an open PR, not merging: the
rules above on merging and on closing issues still apply.
