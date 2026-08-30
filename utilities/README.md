# utilities/

Standalone maintenance scripts for this repo. Unlike `.specify/scripts/`
(which back the spec-kit slash-command workflow and are invoked by Claude
Code hooks/skills) and `infrastructure/scripts/` (which target the deployed
environment), scripts here are run directly by a human from the repo root
when local developer state needs tidying up. Each script documents its own
use case, safety model, and options in a header comment — read that before
running.

## Scripts

- **`cleanup-branches-worktrees.sh`** — Deletes local git branches and
  worktrees that are safe to remove (their PR is merged/closed on GitHub, or
  they're merged into the default branch), while leaving anything active or
  unconfirmed alone. Dry-run by default; see the script header for the full
  safety model. Run it when `git branch` or `git worktree list` gets
  cluttered, or periodically after a batch of PRs merge.

  ```sh
  utilities/cleanup-branches-worktrees.sh          # dry-run report
  utilities/cleanup-branches-worktrees.sh --yes     # perform safe cleanup
  utilities/cleanup-branches-worktrees.sh -h        # full usage/docs
  ```
