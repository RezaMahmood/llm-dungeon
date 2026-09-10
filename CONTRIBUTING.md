# Contributing to LLM Dungeon Adventure

This document describes how a change gets from an idea to `main`: the
governance it must satisfy, where the work happens, and what the merge
gate actually checks.

The authority is the project constitution
([`.specify/memory/constitution.md`](.specify/memory/constitution.md)).
Where this file and the constitution disagree, the constitution wins.
Claude Code sessions additionally follow [`CLAUDE.md`](CLAUDE.md), which
is the operational form of the same rules.

---

## 1. Governance & development principles

1. **Pull-request-only changes.** Direct commits and pushes to `main` are
   blocked by a GitHub branch ruleset. Branch deletion and non-fast-forward
   pushes to `main` are blocked too.
2. **Automated CI gating.** Every pull request runs the automated checks
   below; a pull request cannot merge while a required check is failing.
3. **Review before merge.** This project has one maintainer, so the
   ruleset requires **zero approving reviews** — the review pass is
   Claude Code's `/code-review` skill, run explicitly before merge, and
   the maintainer weighs its findings alongside the checks. See
   [§5 Review](#5-review) for which tier a change warrants.
4. **Squash merges only.** The pull request title becomes the sole commit
   on `main` and is the only input `semantic-release` reads. See
   [§4 PR titles](#4-pr-titles-conventional-commits). Note that the
   ruleset currently still permits merge commits and rebase merges, so
   this one is discipline rather than a guard rail — merging any other way
   loses the title and with it the version computation.
5. **AI agent division of labour.** A local AI agent (Claude Code or
   similar) may write the change, push the branch and open the pull
   request, and must label it `AI Generated` and `Claude`. It must not
   merge a pull request or enable auto-merge — merging is the
   maintainer's manual action. Constitution Principle XIII.
6. **No admin bypasses.** Branch rules apply uniformly.

---

## 2. Where the work happens

Spec/feature work runs inside that feature's own git worktree and that
worktree's own devcontainer:

```bash
bin/wt <branch-name>          # creates .worktrees/<branch>, starts its container
```

A session for one spec then has no filesystem path to any other spec's
worktree. Branch work with no `specs/<branch>/` folder (`chore/*`,
`fix/*`, `docs/*`, `perf/*`) may instead be done in the primary checkout,
on a branch — never on `main`.

Housekeeping, run from the primary checkout:

```bash
bin/wt-prune                  # dry run: worktrees/branches whose PR is merged
bin/wt-prune --yes            # actually remove them
bin/wt-sync                   # worktrees running stale CLAUDE.md/constitution/hooks
```

Full details, including the container auth mounts and the known limits of
the isolation: [`docs/WORKTREE_CONTAINER_WORKFLOW.md`](docs/WORKTREE_CONTAINER_WORKFLOW.md).

---

## 3. Standard PR workflow

### Step 1 — branch from the latest `main`

```bash
git switch main
git pull --ff-only
git switch -c fix/my-change
```

### Step 2 — implement and test locally

```bash
pytest -v                      # backend
cd src/frontend && npm test    # frontend
```

### Step 3 — open the pull request

```bash
git push -u origin fix/my-change
gh pr create --title "fix(backend): stop replaying the opening narrative" --body "..."
```

The title must be Conventional Commits with a scope — see §4. The
description should say what problem the change addresses, what was
decided, what was actually tested and what it returned, and anything
deliberately left undone. It must not contain PII (Principle X).

### Step 4 — checks and review

Required status checks, all of which must pass:

| check | what it covers |
|---|---|
| `test` | backend and frontend test suites |
| `check-title` | the PR title's Conventional Commits format and allowed type/scope |
| `actionlint` | GitHub Actions workflow syntax |
| `structure-test` | workflow job/step shape, non-testable-change detection, the warm-window schedule, and the worktree hook/lifecycle scripts |
| `release-fixtures-test` | semantic-release version-computation fixtures |

The ruleset also requires branches to be up to date with `main` before
merge, and dismisses stale reviews on push. Then run the review pass
(§5).

### Step 5 — merge

The maintainer merges, using **Squash and merge**. The squash commit's
subject is the pull request title.

---

## 4. PR titles (Conventional Commits)

Because the repository merges by squash, the PR title *is* the commit on
`main`, and `semantic-release` computes the next version from it. There
is no second chance to encode intent in individual commit messages.

Format: `type(scope): description`, or `type(scope)!: description` for a
breaking change. **Scope is required**, even where it never gates a
version bump — `feat: add a thing` fails `check-title`.

- **type:** `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`,
  `build`, `ci`, `style`, `revert`
- **scope:** `frontend`, `backend`, `infra`, `ci`, `specs`, `deps`,
  `deps-dev`, `docs`

Version effects:

| title | effect |
|---|---|
| `feat(backend)` / `feat(frontend)` | minor bump for that component |
| `fix(...)` / `perf(...)` on those scopes | patch bump for that component |
| `!` after the scope, or a `BREAKING CHANGE:` footer | major bump |
| any other type or scope | no release |

The lists above are mirrored from
[`scripts/pr-title-config.js`](scripts/pr-title-config.js), which is the
single source of truth (`.github/workflows/pr-title-check.yml` mirrors it
too). Releases are additionally gated by path-diff filtering, so a
`feat(backend)` title cuts no backend release if no backend paths
changed.

---

## 5. Review

Review is triaged rather than all-or-nothing — `/code-review ultra <PR#>`
runs a multi-agent cloud review and is billed per run. The full triage
table, including how the authoring model shifts the tier, is in
[`CLAUDE.md`](CLAUDE.md#code-review-triage). In short:

| the change | minimum tier |
|---|---|
| docs, comments, spec prose | none |
| small, single-component, covered by green tests | `/code-review` |
| large, multi-component, or new module/dependency | `/code-review high` |
| auth, secrets, permissions, CI/CD, deploy, infrastructure, persisted-data schema, release machinery, governance files | `/code-review ultra <PR#>` |

The highest applicable row wins. The review posts findings as
recommendations; it does not produce an approving review and does not
merge.

---

## 6. Reference

- [Per-worktree devcontainer workflow](docs/WORKTREE_CONTAINER_WORKFLOW.md)
- [Project constitution](.specify/memory/constitution.md)
- [Claude Code instructions (`CLAUDE.md`)](CLAUDE.md)
- [CI/CD validation guide](specs/001-ci-cd-foundation-done/quickstart.md)
- [CI/CD troubleshooting guide](docs/CI_CD_TROUBLESHOOTING.md)
- [GitHub Actions workflows documentation](.github/workflows/README.md)
