# CLAUDE.md

Project-wide instructions for Claude Code sessions in this repo, including
sessions running inside per-worktree devcontainers (see
[`docs/WORKTREE_CONTAINER_WORKFLOW.md`](docs/WORKTREE_CONTAINER_WORKFLOW.md)).

## Git / PR workflow

Per the constitution's Principle XIII (AI Agent Division of Labor), Claude
Code performs local development and spec-related work, and also pushes and
opens the pull request once that work is ready. Claude MUST NOT merge a
pull request or resolve/close a GitHub issue directly against GitHub itself
— those steps go to GitHub Copilot (review) and the requesting user
(manual merge).

- When local work on a branch is ready, Claude MUST push it and open the
  pull request itself with `gh pr create`.
- Every PR Claude opens MUST be labelled `AI Generated` and `Claude` (both
  labels already exist in this repo), e.g.
  `gh pr create --label "AI Generated" --label "Claude" ...`.
- PR descriptions MUST NOT include a link to the Claude Code session/transcript.
- Claude MUST NOT enable auto-merge and MUST NOT run `gh pr merge` to merge
  directly, and MUST NOT itself monitor the PR through to completion. From
  there, GitHub Copilot reviews the PR and posts its findings as review
  comments/recommendations — Copilot code review does not produce a formal
  approving review or perform the merge. The requesting user reviews Copilot's
  recommendations and the required status checks, then merges the pull
  request manually.
- GitHub issue resolution (bugs, dependency updates, fixes) MUST be handed
  off to GitHub Copilot rather than resolved end-to-end by Claude pushing
  directly to GitHub.

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
