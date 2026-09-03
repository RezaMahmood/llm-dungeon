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
