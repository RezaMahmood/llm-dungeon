# CLAUDE.md

Project-wide instructions for Claude Code sessions in this repo, including
sessions running inside per-worktree devcontainers (see
[`docs/WORKTREE_CONTAINER_WORKFLOW.md`](docs/WORKTREE_CONTAINER_WORKFLOW.md)).

## Git / PR workflow

Per the constitution's Principle XIII (AI Agent Division of Labor), Claude
Code performs local development and spec-related work only. It MUST NOT
create, merge, or monitor pull requests, or resolve GitHub issues, directly
against GitHub itself.

- When local work on a branch is ready, Claude MUST hand off to GitHub
  Copilot to open the pull request, monitor its required status checks,
  and merge it — Claude MUST NOT run `gh pr create` or `gh pr merge` itself.
- GitHub issue resolution (bugs, dependency updates, fixes) MUST likewise
  be handed off to GitHub Copilot rather than resolved end-to-end by Claude
  pushing directly to GitHub.
- PR descriptions MUST NOT include a link to the Claude Code session/transcript.
- Every PR MUST be labelled `AI Generated` and `Claude`. Both labels already
  exist in this repo — pass them along in the handoff to Copilot.
