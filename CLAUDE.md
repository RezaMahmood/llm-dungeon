# CLAUDE.md

Project-wide instructions for Claude Code sessions in this repo, including
sessions running inside per-worktree devcontainers (see
[`docs/WORKTREE_CONTAINER_WORKFLOW.md`](docs/WORKTREE_CONTAINER_WORKFLOW.md)).

This file is the operational form of the constitution
([`.specify/memory/constitution.md`](.specify/memory/constitution.md)) —
Principle XIII and the AI Agent / GitHub Handoff Requirements in
particular. The constitution wins where the two disagree: this file is
then wrong and MUST be corrected, not worked around.

## Where work happens

- **Every branch gets its own worktree.** Whatever the work, it happens
  in `.worktrees/<branch>`, started by the user with `bin/wt <branch>`.
  `bin/wt` is a human entrypoint — Claude MUST NOT invoke it, because it
  execs a new `claude` session. The primary checkout stays on `main` and
  is only for the lifecycle tooling that has to see every worktree at
  once (`bin/wt-prune`, `bin/wt-sync`).
- **Spec/feature work additionally runs in a container.** A speckit
  feature branch (a branch with a matching `specs/<branch>/` folder) MUST
  be worked on inside that worktree's own devcontainer — plain
  `bin/wt <branch>`. A worktree's container is never shared with another
  worktree.
- **Other branch work runs on the host, no container.** `chore/*`,
  `fix/*`, `docs/*`, `perf/*` and `infra` branches carry no spec folder
  and no concurrent-spec contamination risk, so the user starts them with
  `bin/wt <branch> --no-container`: same worktree, same branch rules, no
  Docker. `bin/wt` refuses `--no-container` for a branch that has a spec
  folder.
- **Never work on `main`.** Branch first, whatever the checkout. The
  `SessionEnd` hook returns the primary checkout to `main` when the tree
  is clean; do not fight it, and do not switch branches at the end of a
  session to pre-empt it.
- **Another worktree is off limits.** `.claude/settings.json` denies
  `Read(.worktrees/**)` and `Edit(.worktrees/**)`. Claude MUST NOT read,
  edit or list another worktree's files, and MUST NOT route around the
  deny rules with `Bash` (`cat`, `find`, `git -C`, …). If a task seems to
  need it, say so and let the user do it. In a container-less worktree
  this rule is doing the work alone: a sibling sits at `../<branch>`,
  which those patterns do not match and no mount boundary blocks. Treat
  everything outside the current worktree as another session's, and never
  reach for a relative path that leaves it.
- **Lifecycle tooling.** `bin/wt-prune` removes worktrees, branches and
  containers whose PR GitHub reports as merged; `bin/wt-sync` reports
  worktrees running stale bootstrap files. Claude MAY run either in its
  reporting form (`bin/wt-prune` with no flags is a dry run). Claude MUST
  NOT run `bin/wt-prune --yes` unless the user asks for that run — it
  deletes branches and worktrees.

## Git / PR workflow

Per constitution Principle XIII (AI Agent Division of Labor), Claude Code
performs local development and spec-related work — including resolving a
GitHub issue end-to-end — then pushes the branch and opens the pull
request itself. The GitHub-side review pass is Claude Code's
`/code-review` skill, triggered explicitly (never automatically on push).
It posts findings as recommendations: it produces no formal approving
review and performs no merge. **The requesting user reviews those
findings and the required status checks, then merges manually.**

- When local work on a branch is ready, Claude MUST push it and open the
  pull request itself with `gh pr create`.
- Every PR Claude opens MUST be labelled `AI Generated` and `Claude` (both
  labels already exist in this repo), e.g.
  `gh pr create --label "AI Generated" --label "Claude" ...`.
- Before pushing to a remote branch, Claude MUST check the state of any
  pull request already associated with it (e.g.
  `gh pr view <branch> --json state`). Claude MUST NEVER push to the
  branch of a PR that has already been merged or closed, even if the
  branch still exists and the push would succeed — that work would land
  without anyone being asked to review it. Instead, branch off the current
  `main` and open a new PR for it, labelled as above. Pushing to a branch
  whose PR is still open is fine, and is the normal way to address review
  feedback.
- Claude MUST NOT merge a pull request: not with `gh pr merge`, not by
  enabling auto-merge, and not through the API (`gh api --method PUT
  .../merge`, a `mergePullRequest` mutation). `.claude/settings.json`
  denies the `gh pr merge` forms; the API paths are governed by this rule
  rather than by an enforced one.
- Claude MUST NOT monitor a PR through to completion. Report the checks'
  state once and hand back.
- Claude MAY close a GitHub issue with `gh issue close` only when **both**
  hold: the user has asked Claude to close that issue, and Claude has
  verified the resolving work is merged to `origin/main` — not just on a
  local branch, in a worktree, or in an open PR. Claude MUST say what it
  verified when it closes one, and MUST NOT close an issue on its own
  initiative (e.g. because it judges the work done). If either condition
  fails, leave the issue open and say why.

## PR content contract

A PR description is the only account of the change that survives to
`main`. Every PR Claude opens MUST state, proportionate to the change:

1. **What this is** — the issue or part it belongs to (`Part (c) of #293`).
   Use `Closes #NNN` only when the PR fully resolves that issue **and**
   the user asked for it to close.
2. **The problem** — the observed behaviour or evidence that motivated the
   change, not a restatement of the diff.
3. **What changed** — the decisions taken and why one option won. The file
   list is already in the diff; do not repeat it as prose.
4. **Testing** — what was actually run and what it actually returned.
   Anything not verified MUST be named as unverified. Never describe a
   check that was not run.
5. **Known limits / follow-ups** — what was deliberately left undone, and
   why.
6. **Recommended review tier** — per the triage table below, with the
   reason it applies.

A one-line docs fix does not need six headings, but items 1, 4 and 5 are
never optional. A PR description MUST NOT:

- link to the Claude Code session/transcript;
- contain PII (Principle X) — reference records indirectly;
- claim a status check passed that Claude did not observe pass, or quote
  numbers it did not measure;
- assert an approving review, or ask the user to merge — the user decides
  when, and merging is theirs alone.

Finish the description with the attribution footer:
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## PR title format

This repo merges exclusively by squash, so the PR title — not any
individual commit message — becomes the sole commit on `main` and is what
`semantic-release` reads to compute the next version. Every PR title
Claude opens (via `gh pr create --title ...`) MUST follow Conventional
Commits format, `type(scope): description` (optionally `type(scope)!:`
for a breaking change), and MUST pass the required `check-title` status
check (`.github/workflows/pr-title-check.yml`) before merge.

- **Allowed `type`:** `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`,
  `test`, `build`, `ci`, `style`, `revert`.
- **Allowed `scope`:** `frontend`, `backend`, `infra`, `ci`, `specs`,
  `deps`, `deps-dev`, `docs`. Scope is required on every PR title, even
  for a scope that never gates a version bump.
- The single source of truth for these lists is `scripts/pr-title-config.js`
  (mirrored into `.github/workflows/pr-title-check.yml`) — check there if
  unsure, rather than inventing a new scope (e.g. a repo-tooling/config
  change like `.claude/`, `.specify/`, or hooks belongs under `infra`, not
  a bespoke scope).
- `feat(backend|frontend)` → minor bump for that component; `fix`/`perf(backend|frontend)` → patch bump; a `!` after the scope (or a `BREAKING CHANGE:` footer) → major bump.
- Note: the declared scope is descriptive only; releases are additionally gated by path-diff filtering, so a `feat(backend)` title won’t cut a backend release if no backend paths changed.

## Code review triage

Review is not all-or-nothing. `/code-review ultra <PR#>` runs a
multi-agent cloud review and is billed per run; `/code-review` on its own
runs locally at the level last used. Match the tier to the change instead
of defaulting to either extreme.

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
- governance: the constitution, this file, `CONTRIBUTING.md`;
- persisted data: schema, migrations, or anything that can delete or
  rewrite existing records;
- release machinery: `scripts/pr-title-config.js`, `.releaserc.json`.

**Then adjust for how the change was authored:**

- written by an Opus-class model with the relevant tests run green — tier
  as the table says;
- written by a smaller/faster model, or produced by a long unattended run
  nobody watched — **one tier up**;
- mechanical and independently verified (a rename with a green build, a
  revert of an already-reviewed commit, a dependency bump with a passing
  suite) — **one tier down**, never below `none`.

Where two rows apply, the **highest** tier wins. Claude names the
resulting tier in the PR description (contract item 6) and MAY run the
local tiers itself. Claude MUST NOT attempt to launch `ultra` — it is
user-triggered and billed; ask the user to run
`/code-review ultra <PR#>` instead.

## Responding to code-review findings

PR code review runs via Claude Code's `/code-review` skill — either as inline PR
review comments (`--comment`) or as a single posted comment (`/code-review ultra
<PR#> --post`). When the user hands Claude a link to that review (or an individual
finding) on one of Claude's PRs, and Claude then fixes the underlying issue and
pushes the fix:

- If the finding is an inline review comment thread, reply on that specific thread
  (not just the PR generally) summarizing the fix and the commit it landed in, e.g.
  `gh api repos/{owner}/{repo}/pulls/{pr}/comments -f body="..." -f in_reply_to={comment_id}`,
  then mark the thread resolved via the GraphQL `resolveReviewThread` mutation
  (look up the thread id with a `reviewThreads` query first if only the comment
  id/URL is known), e.g.
  `gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "..."}) { thread { isResolved } } }'`.
- If the finding was posted as a single PR comment, reply as a normal PR comment
  summarizing the fix and the commit it landed in.
- Resolving a review thread this way is addressing feedback on an open PR, not
  merging — the restriction above on merging still applies, as do the conditions
  on closing an issue.
- If a finding is out of scope, already handled elsewhere, or a fix isn't
  warranted, reply explaining why instead of silently resolving it, and leave
  it for the user to decide.
