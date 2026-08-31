# Per-worktree isolated devcontainer workflow

Each spec/feature gets its own git worktree, and each worktree gets its
own devcontainer. Claude Code runs *inside* that container, so a session
working on one spec has no filesystem path to any other worktree — it's a
physical guarantee, not just a convention. See
[`.specify/memory/constitution.md`](../.specify/memory/constitution.md)
(Development Workflow & Quality Gates) for the rule this enforces, and
`bin/wt` for the script that implements it.

## Prerequisites (one-time, per machine)

- Docker Desktop (or another Docker engine) running.
- The devcontainer CLI: `npm install -g @devcontainers/cli`.
- `bin/wt` on your `PATH`, or just call it as `bin/wt` from the repo root
  or any of its worktrees (it resolves the primary repo root itself).

## Day to day: starting work on a spec

1. Open a **new iTerm2 tab or window** for this spec — one terminal per
   spec/worktree, not multiple sessions sharing one terminal (see the
   `wt()` shell helper below to make this a single command).
2. From anywhere inside the repo (primary checkout or another worktree),
   run:

   ```bash
   bin/wt <branch-name>
   ```

   First time for that branch: creates `.worktrees/<branch-name>` (from
   `main` by default — see **Dependent specs** below), builds/starts its
   container, and execs `claude` inside it. Every later run against the
   same branch just resumes the existing worktree and container — fast.
3. You're now talking to Claude Code running inside a container whose
   filesystem view is *only* this worktree (plus the shared `.git`). `cd
   ..` or `ls ../other-branch` inside that session has nothing to find —
   that's the isolation working, not a bug.
4. When you exit the `claude` session (Ctrl-D / `exit`), `bin/wt` stops
   (not removes) the container automatically. Nothing to clean up by
   hand for a normal end-of-session.

## Dependent specs (spec B needs spec A's in-flight work)

Don't rely on anything detecting this for you — branch B from A
explicitly:

```bash
bin/wt B --base=A
```

B's worktree/branch now starts from A's *committed* history. B still
can't see A's uncommitted edits (those exist only in A's own container's
working tree) — if B needs something from A, commit it in A first (a WIP
commit is fine).

## Checking for unanticipated overlap between active specs

An isolated worktree container can't see other specs by design. To check
whether two *independently started* specs have drifted into touching the
same files, run this from the **primary repo root** (not from inside any
worktree's container — `bin/wt` never puts you there), where every active
worktree is visible on disk under `.worktrees/`:

```bash
git -C .worktrees/<branch-a> diff main --stat
git -C .worktrees/<branch-b> diff main --stat
```

or ask Claude to do this comparison for you from a primary-root session
(one *not* started via `bin/wt`). Actual merge conflicts, if any, still
surface normally at merge/rebase time regardless.

## Reviewing in VS Code

Open `.worktrees/<branch-name>` in VS Code and choose **"Reopen in
Container"**. It attaches to the *same* running container `bin/wt`
started (both key off the workspace-folder path) — you get the identical
environment Claude is using, and it won't spin up a duplicate container.

For quick read-only browsing of specs/diffs, you don't need the
container at all — just open the folder directly.

## Finishing a spec

Run `/speckit-mark-done` as usual. Once a spec's folder is renamed to
`-done`, its devcontainer is also removed as part of that cleanup (the
worktree itself is left alone, per that skill's existing behavior — see
[`speckit-mark-done`](../.claude/skills/speckit-mark-done/SKILL.md)).

## Cleaning up orphaned containers

If a worktree's branch/directory was removed some other way and its
container was left behind, sweep it from the primary repo root:

```bash
.specify/scripts/bash/prune-worktree-containers.sh
```

## Forcing a rebuild

If the devcontainer image or config changed and a worktree's container
needs to be recreated from scratch:

```bash
bin/wt <branch-name> --rebuild
```

## A shell for running tests/tools without Claude

```bash
bin/wt <branch-name> --shell
```

Drops into an interactive shell inside that worktree's container instead
of `claude` — same isolation, same caches.

## Optional: one iTerm2 tab per spec, one command

Add to your shell profile (`~/.zshrc`):

```bash
wt() {
  osascript -e "tell application \"iTerm2\"
    tell current window
      set newTab to (create tab with default profile)
      tell current session of newTab
        write text \"cd $(pwd) && bin/wt $1\"
        set name to \"$1\"
      end tell
    end tell
  end tell" >/dev/null
}
```

`wt <branch-name>` from any terminal then opens a *new* iTerm2 tab titled
after the branch and starts that worktree's session in it — so many
concurrent specs stay visually distinguishable across tabs without any
extra bookkeeping.

## Shared caches

The uv download cache and Terraform provider plugin cache are Docker
named volumes shared across *every* worktree's container (declared in
[`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json)),
so `uv sync` / `terraform init` only pay the download cost once, not per
worktree. The container image itself is also shared — `devcontainer up`
keys the built image off `devcontainer.json` content, not the workspace
path, so the azure-cli/dotnet/terraform/gh feature layers build once
regardless of how many worktrees you have open. Only `.venv` stays
per-worktree (not shared), since different branches may pin different
dependency versions.

## Verified end-to-end (2026-08-31)

Built and ran a real worktree/container through this whole workflow while
writing it. Confirmed working: `git status`/`git log` inside a container
that only has this one worktree mounted (via `--mount-git-worktree-common-dir`
+ `git worktree add --relative-paths`); `/workspaces` inside the container
shows only this worktree, no siblings; `WORKTREE_CONTAINER` reaches the
session and `check-worktree-sync.sh`'s container-identity check correctly
blocks on a mismatch and passes on a match; `~/.claude` auth carried over
from the host with no `claude login` needed (this host stores it as files,
not in the macOS keychain — still verify on yours). Two real bugs turned up
and are already fixed in this repo, not just noted here:

- The `~/.claude` mount was originally read-only (to protect host
  credentials). The `claude` installer needs to write its download cache to
  `~/.claude/downloads`, so a read-only mount made it fail with a misleading
  `curl` write error, not an obvious permissions error. Now mounted
  read-write (`.devcontainer/devcontainer.json`) — an accepted tradeoff for
  a personal dev container, the same as the common `~/.ssh`/`~/.gitconfig`
  mount pattern.
- Docker auto-creates a *new* named volume's mount point (e.g. `~/.cache`,
  the parent of the `uv` cache volume) as root, even though this image's
  default user is `vscode` — so the `claude` installer failed with `EACCES`
  writing to `~/.cache/claude`, a sibling directory. `.devcontainer/post-create.sh`
  now `sudo chown`s both cache-volume mount points before installing
  anything.

## Known gaps to verify on your machine

- **Docker Desktop's own VM disk, not your Mac's disk.** While testing,
  Docker Desktop's virtual disk was at 561MB free of 59GB even though the
  host Mac had 63GB+ free — `docker system df` showed ~12GB in stopped
  containers and ~10GB of reclaimable build cache. This is what actually
  bit the `claude` binary download (a few hundred MB) before the two fixes
  above. Check yours with `docker system df` before your first `bin/wt`
  run; free space with `docker system prune` (asks before deleting
  anything) or raise the disk limit in Docker Desktop → Settings →
  Resources.
- If Claude Code's credential is stored in the macOS keychain rather
  than a file under `~/.claude` on your machine, the mount won't carry
  auth in — run `claude login` (or set `ANTHROPIC_API_KEY`) inside the
  container once if `bin/wt` fails to authenticate.
- The container-removal filters in `bin/wt`, `prune-worktree-containers.sh`,
  and `speckit-mark-done` match on the `devcontainer.local_folder` label —
  confirmed as the real label the devcontainer CLI sets by default while
  testing (`docker inspect <container> --format '{{json .Config.Labels}}'`
  if cleanup ever seems to miss one).
- `devcontainer.json` / `bin/wt` / the hook scripts only take effect in a
  worktree once they're *committed* — a worktree checks out committed
  content from its branch, so uncommitted edits to these files on `main`
  won't appear in a worktree created before that commit lands.
