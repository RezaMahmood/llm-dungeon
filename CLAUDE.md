# CLAUDE.md

Project-wide instructions for Claude Code sessions in this repo, including
sessions running inside per-worktree devcontainers (see
[`docs/WORKTREE_CONTAINER_WORKFLOW.md`](docs/WORKTREE_CONTAINER_WORKFLOW.md)).

## Git / PR workflow

- Every `git push` of a branch MUST be followed by opening a pull request
  for it (`gh pr create`) — never leave a pushed branch without an open PR.
- PR descriptions MUST NOT include a link to the Claude Code session/transcript.
- Every PR created by Claude MUST be labelled `AI Generated` and `Claude`
  (e.g. `gh pr create --label "AI Generated" --label "Claude" ...`). Both
  labels already exist in this repo.
- Claude MAY merge a PR it opened without asking for confirmation first,
  once all required status checks report success
  (`gh pr checks <pr> --required` or equivalent). Merge with
  `gh pr merge --squash --delete-branch`. This authorization covers only
  PRs Claude itself opened in the current session's line of work — still
  ask before merging a PR opened by someone else, or one with failing/
  pending required checks.
