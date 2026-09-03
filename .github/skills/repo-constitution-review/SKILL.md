---
name: repo-constitution-review
description: Use this during code review of every pull request in this repository, to check the PR title against this repo's Conventional Commits and semantic-versioning conventions, and — for changes touching .github/workflows/**, repository/CI configuration, or GitHub Actions — workflow security, PR/commit hygiene, and the AI-agent GitHub handoff process. Checks GitHub- and CI/CD-specific rules from this project's constitution that a generic review would not know to check. Does not review application code, UI, or in-progress feature implementation.
license: N/A
---

# Repo constitution review — GitHub & CI/CD

This repo's binding rules live in `.specify/memory/constitution.md`. This
skill is a narrow, second guard focused only on GitHub platform mechanics
and CI/CD — not application code quality, UI/design, telemetry, or other
in-progress implementation details, which are expected to evolve freely
while a feature is being built. Only apply the sections below relevant to
what actually changed in the diff.

Read `.specify/memory/constitution.md` for full rationale before making a
judgment call; the checklist below is a pointer into it, not a replacement
for it. When a rule below is violated, cite the specific constitution
principle/section in the review comment (e.g. "Principle V") so the author
can find the source of truth.

## GitHub Actions workflow changes (`.github/workflows/**`)

- **Actions are pinned to a version tag** (this repo's existing convention,
  e.g. `actions/setup-node@v7`, `azure/login@v3`) — flag a new `uses:` step
  pinned to a floating ref (`@main`, `@master`, no ref) or an unfamiliar
  third-party action from outside GitHub/Azure/HashiCorp-owned namespaces
  without comment.
- **No secrets/credentials committed into workflow YAML.** Deployment
  credentials and config MUST come from GitHub Actions secrets or
  environment secrets/variables (Environments & Deployment Pipeline), never
  a literal value in the workflow file.
- **CI MUST run on every PR and gate merge (Principle V).** A change to
  `test.yml`, `workflow-lint.yml`, `workflow-structure-test.yml`, or
  `pr-title-check.yml` that narrows trigger conditions (e.g. adds a path
  filter that could skip required checks, changes `pull_request` to
  `pull_request_target` without clear justification, or removes a job) is a
  blocking finding unless explained in the PR description.
- **Deploy workflows only run after required checks pass** (Environments &
  Deployment Pipeline) — a deploy workflow (`backend-deploy.yml`,
  `frontend-deploy.yml`, `infrastructure-deploy.yml`) must not be
  restructured to trigger independently of the build/test gate.
- **No new persistent environment** beyond local dev and the single live
  environment (Principle XII) — question a new workflow that stands up a
  staging/UAT/QA deployment target.
- Reusable workflow calls (`_build-backend.yml`, `_build-frontend.yml`)
  should stay called via `uses: ./.github/workflows/...`, not duplicated
  inline.

## Dependency / supply-chain changes affecting CI

- `requirements.txt`, `package.json`/`package-lock.json`, and Dockerfiles
  MUST pull only from official public registries and MUST include a
  matching lockfile change alongside any manifest change (Dependency &
  Supply Chain Security Requirements).
- Don't introduce or bump to a dependency version already flagged with a
  known unpatched critical/high-severity advisory when a fixed version
  exists.
- Dependabot must remain enabled/configured (`.github/dependabot.yml`) —
  flag a PR that disables or narrows it without explanation.

## PR title conventions

- **Format:** `type(scope): description`, optionally `type(scope)!:` for a
  breaking change — enforced by the `check-title` job
  (`.github/workflows/pr-title-check.yml`, via
  `amannn/action-semantic-pull-request`), sourced from
  `scripts/pr-title-config.js`. Scope is always required, even for a scope
  that never gates a version bump.
- **Allowed `type`:** `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`,
  `test`, `build`, `ci`, `style`, `revert`.
- **Allowed `scope`:** `frontend`, `backend`, `infra`, `ci`, `specs`,
  `deps`, `deps-dev`, `docs`. `frontend`/`backend` are the two scopes that
  actually drive a version bump (see Semantic versioning below); the rest
  must still be format-valid but never gate a release.
- Flag a title that doesn't match this pattern, uses a type/scope outside
  these lists, or picks a `type`/`!` that doesn't match what the diff
  actually does (e.g. `fix(backend)` on a change that's really a new
  feature, or a breaking API/schema change not marked `!`).

## Semantic versioning conventions

- This repo merges exclusively by squash, so **the PR title becomes the
  sole commit on `main`** and is the only input `semantic-release` reads to
  compute the next version — there's no second chance to encode intent via
  individual commit messages.
- Versioning is per-component, not repo-wide: `src/backend/.releaserc.json`
  and `src/frontend/.releaserc.json` each run `semantic-release` via
  `semantic-release-monorepo`, tagging independently as
  `backend-v${version}` / `frontend-v${version}` based on the Angular
  commit-analyzer preset:
  - `feat(backend|frontend)` → minor bump for that component.
  - `fix(backend|frontend)` or `perf(backend|frontend)` → patch bump.
  - A `!` after the scope (or a `BREAKING CHANGE:` footer) → major bump.
  - Any other type (`chore`, `docs`, `refactor`, `test`, `build`, `ci`,
    `style`, `revert`) or any non-`frontend`/`backend` scope → no release
    triggered for that PR.
- Flag a PR whose title's type/scope would silently suppress a version bump
  the change actually warrants (e.g. a real backend behavior change titled
  `chore(backend): ...` or scoped outside `backend`/`frontend`), or that
  would trigger an unwarranted bump (e.g. `feat(frontend)` on a docs-only
  change).

## PR / commit / issue hygiene (GitHub artifacts, not code)

- **No PII in PR descriptions, comments, commit messages, or issues**
  (Principle X) — GitHub history here is effectively permanent and broadly
  accessible; a record involving PII should be referenced indirectly
  (role/internal ID) rather than by name/email/etc.
- **No direct pushes to `main`** — all changes go through a PR (Development
  Workflow & Quality Gates).

## AI-agent GitHub handoff (Principle XIII)

- A PR opened by a local AI agent (Claude Code or similar) MUST be labelled
  `AI Generated` and `Claude`, MUST NOT link to the agent's own
  session/transcript in the description, and MUST have auto-merge enabled
  rather than being merged directly by that agent.
- The local agent must not itself merge a PR or close/resolve a GitHub
  issue — that's GitHub Copilot's job. Note it if a PR's history shows the
  opening actor also merging it or closing an issue directly.
