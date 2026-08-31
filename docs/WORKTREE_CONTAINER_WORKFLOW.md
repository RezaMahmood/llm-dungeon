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
blocks on a mismatch and passes on a match; Claude Code and `gh` CLI auth
both carried over from the host with no interactive login needed,
including across a `--rebuild` (verified by force-recreating containers
and running `claude -p "..."` non-interactively — no login prompt).
Four real bugs turned up and are already fixed in this repo, not just
noted here:

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
- Recreating a container (`bin/wt --rebuild`, or after cleanup) forced a
  fresh `claude login` even though `~/.claude/.credentials.json` looked
  mounted and present. Cause: Claude Code's oauth account/onboarding state
  (`oauthAccount`, `hasCompletedOnboarding`, ...) lives in a *sibling*
  file, `~/.claude.json`, not inside the `~/.claude` directory — so it
  wasn't covered by the existing mount, and each new container got its own
  empty one. Fixed by adding a second bind mount for that file
  (`.devcontainer/devcontainer.json`); see **Claude Code auth inside the
  container** below.
- The `gh` CLI (from the `github-cli` feature) asked for `gh auth login`
  in every container, with no way to persist it — nothing mounted
  `~/.config/gh`, where `gh` keeps its own login independent of any OS
  keychain. Fixed the same way, with a third bind mount; see **`gh` CLI
  auth inside the container** below.
- The container-removal filters in `bin/wt`, `prune-worktree-containers.sh`,
  and `speckit-mark-done` match on the `devcontainer.local_folder` label —
  confirmed as the real label the devcontainer CLI sets by default while
  testing (`docker inspect <container> --format '{{json .Config.Labels}}'`
  if cleanup ever seems to miss one).

## Docker Desktop resources

Docker Desktop's VM has its own disk/CPU/memory allocation, separate from
the host Mac's — a resource crunch shows up there even when the host has
plenty free. While first writing this workflow, the VM disk was at 561MB
free of 59GB (host had 63GB+ free); `docker system df` showed ~12GB in
stopped containers and ~10GB of reclaimable build cache, and that's what
actually broke the `claude` binary download (a few hundred MB) before the
two fixes above.

Resources have since been raised in Docker Desktop → Settings → Resources;
re-checked 2026-08-31 with `docker system df` and a throwaway container's
`df -h /` showing 93G+ free of 125G on the VM disk. If it ever gets tight
again: `docker system df` shows what's reclaimable, `docker system prune`
frees it (asks before deleting anything), and the same Settings → Resources
panel raises the disk/CPU/memory ceiling.

## Claude Code auth inside the container

`bin/wt` bind-mounts two things from the host so a container never needs
its own `claude login`, including across a `--rebuild` or after cleanup
recreates it from scratch (`.devcontainer/devcontainer.json`):

- `~/.claude` → `/home/vscode/.claude` — holds
  `~/.claude/.credentials.json` when the host stores its credential as a
  file.
- `~/.claude.json` → `/home/vscode/.claude.json` — a *sibling* file (not
  inside the `~/.claude` directory), holding the oauth account/onboarding
  state (`oauthAccount`, `hasCompletedOnboarding`, ...). Mounting only
  `~/.claude` and not this file was the original bug: each new container
  got its own empty `~/.claude.json`, so it looked authenticated
  (credentials present) but wasn't, and any container recreation forced a
  fresh login. Both mounts together are what actually fixes it — verified
  2026-08-31 by force-recreating a container and running
  `claude -p "..."` non-interactively with no login prompt.

Both mounts only carry auth in if the host's credential is stored as a
**file** in the first place. On Linux/Windows that's always true. On
macOS, Claude Code prefers the Keychain by default and only falls back to
`~/.claude/.credentials.json` when the Keychain is unavailable (locked,
headless/SSH session, or a Keychain write failure) — there's no setting to
force file-based storage ahead of time. Check what your host is actually
using:

```bash
security find-generic-password -s "Claude Code-credentials" 2>&1 | head -1
```

If that finds an entry, your credential lives in the Keychain and neither
mount carries anything in — `bin/wt` will need one of:

- `claude login` run once inside the container (writes its own
  `~/.claude/.credentials.json` and `~/.claude.json` inside the
  container's filesystem, independent of the host Keychain — note this
  container-local state does *not* survive `--rebuild`, since the mounts
  don't cover it), or
- an `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` environment variable, or
- an `apiKeyHelper` script referenced from Claude Code settings.

This host (verified 2026-08-31) stores its credential as
`~/.claude/.credentials.json`, not the Keychain, so both mounts carry auth
in with no extra step — still verify on yours with the command above
before assuming it'll "just work".

### Recovering from "Claude configuration file not found"

The `~/.claude.json` mount above is a *single-file* bind mount, unlike the
directory mounts (`~/.claude`, `~/.config/gh`). Claude Code saves that file
atomically (backup + temp file + `rename()` over the real path), and Docker
Desktop's virtiofs/osxfs bind mounts can lose track of a single file across
a rename like that -- so a container can occasionally come back saying the
config file is missing even though a backup exists right next to it
(`~/.claude/backups/.claude.json.backup.<timestamp>`).

`.devcontainer/restore-claude-config.sh` runs on every container start
(`postStartCommand`, which fires on resume too, not just first creation)
and restores the newest backup automatically if the live file is missing --
you shouldn't need to run the `cp` command from the warning by hand. If you
ever do see it fail to restore, the backups directory still has everything
needed to fix it manually.

## `gh` CLI auth inside the container

Same problem, same fix, one more tool: the `github-cli` devcontainer
feature installs `gh`, but nothing carried its login in until
`~/.config/gh` (where `gh` stores `hosts.yml` with its oauth token, on any
OS — no keychain involved) was added as a bind mount alongside the two
Claude ones (`.devcontainer/devcontainer.json`). Before that fix, every
container asked for `gh auth login` fresh, every time.

Unlike `~/.claude.json`, this mount doesn't need the host path to already
exist — Docker creates `~/.config/gh` on the host automatically the first
time the mount is used, even if you've never run `gh` on the host itself.
Run `gh auth login` **once**, inside any worktree's container, and it
persists to the host and is picked up by every other worktree's container
from then on (including through `--rebuild`) — verified 2026-08-31 by
inspecting the mount on a freshly built container.

## `devcontainer.json` changes only apply once committed

`devcontainer.json` / `bin/wt` / the hook scripts only take effect in a
worktree once they're *committed* — a worktree checks out committed
content from its branch, so uncommitted edits to these files on `main`
won't appear in a worktree created before that commit lands.
