# Per-worktree workflow

**Every branch gets its own worktree. Only spec branches also get a
container.**

Each branch — spec, chore, fix, docs, perf — gets its own git worktree,
so several pieces of work can be in flight at once and no session's
branch switch ever moves the ground under another. The primary checkout
stays on `main` and is reserved for the lifecycle tooling that has to see
every worktree at once.

On top of that, each *spec/feature* worktree gets its own devcontainer.
Claude Code runs *inside* that container, so a session working on one
spec has no filesystem path to any other worktree — a physical
guarantee, not just a convention. Non-spec work carries no cross-spec
contamination risk, so it skips the container and runs on the host in its
own worktree (`--no-container`) — no Docker, no image build, no
`postCreate`.

That split is deliberate: paying a container for a one-line docs fix is
what used to push that work back into the primary checkout, where it
queued behind everything else and got branched from whatever `HEAD`
happened to be.

See [`.specify/memory/constitution.md`](../.specify/memory/constitution.md)
(Development Workflow & Quality Gates) for the rule this enforces, and
`bin/wt` for the script that implements it.

## Prerequisites (one-time, per machine)

- The Claude Code CLI on the host (needed by `--no-container` sessions;
  container sessions get their own copy via `postCreate`).
- Docker Desktop (or another Docker engine) running — **only** for spec
  branches. A `--no-container` run never touches Docker and does not
  check for it.
- The devcontainer CLI: `npm install -g @devcontainers/cli` — likewise
  only needed for spec branches.
- `bin/wt` on your `PATH`, or just call it as `bin/wt` from the repo root
  or any of its worktrees (it resolves the primary repo root itself).

## Which command do I run?

| The branch | Command | What you get |
|---|---|---|
| Named `<number>-<slug>`, or has a `specs/<branch>/` folder | `bin/wt <branch>` | Worktree **+ its own container**. Required — `bin/wt` refuses `--no-container` here. |
| `chore/*`, `fix/*`, `docs/*`, `perf/*`, `infra` | `bin/wt <branch> --no-container` | Worktree, `claude` on the host, no Docker. |
| `main` | — | Never. `bin/wt` refuses the trunk outright. |

Both forms create the worktree the same way, enforce the same
directory-name-equals-branch-name rules, and run the same
constitution-staleness gate. The only difference is where the session
runs.

**How `bin/wt` decides a branch is spec work** — two signals, either one
enough:

- **The branch name**, speckit's `<number>-<slug>` form. This is the only
  signal available before the work exists: a brand-new spec branch has no
  `specs/` folder until `/speckit-specify` creates one from inside the
  session, so a folder test alone would wave the whole spec-authoring
  session through and catch it only on the *second* start. Refused in
  preflight, before any worktree is made.
- **A `specs/<branch>/` folder in the worktree.** Catches a spec branch
  named against convention, so a `chore/*` name cannot opt real spec work
  out of isolation. This one can only run after the worktree exists, so
  the refusal leaves that worktree behind — harmless, and plain
  `bin/wt <branch>` picks it straight back up.

`--no-container` and `--rebuild` cannot be combined — there is no
container to rebuild.

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

## Run logs (`.wt-logs/`)

Every `bin/wt` run writes to `.wt-logs/` in the **primary checkout**
(gitignored). Before this existed, everything `bin/wt` and `devcontainer
up` printed went to the terminal and nowhere else — so a container that
failed to build, or a `postCreateCommand` that gave up installing
`claude`, left no trace at all once the scrollback was gone.

```
.wt-logs/events.jsonl                  one JSON object per event, all runs
.wt-logs/run-<branch>-<run-id>.log     full transcript of one run
```

Each event carries a stable `code`, so the question is not "what did that
message say" but "what *kind* of failure is this, and how often has it
happened":

```bash
bin/wt --logs        # problem counts by code, plus the last 20 events
bin/wt --logs 100    # ...last 100 instead
```

| code | what it means |
|---|---|
| `E_DOCKER_DOWN` | no reachable Docker daemon — Docker Desktop is asleep |
| `E_NO_DEVCONTAINER_CLI` / `E_NO_DOCKER_CLI` | that CLI isn't on `PATH` |
| `E_CONTAINER_UP` | `devcontainer up` failed; the CLI's own message and description are captured with it |
| `E_CLAUDE_MISSING` | the container exists but has no `claude` — `postCreate` failed at creation and never re-runs (see below) |
| `E_CLAUDE_MISSING_HOST` | a `--no-container` run found no `claude` on the host's `PATH` |
| `E_SPEC_NEEDS_CONTAINER` | `--no-container` was used on spec work — a `<number>-<slug>` branch name, or a `specs/<branch>/` folder — which must be isolated |
| `E_FLAG_CONFLICT` | `--no-container` and `--rebuild` were given together; there is no container to rebuild |
| `E_BRANCH_PATH_MISMATCH`, `E_PATH_BRANCH_MISMATCH`, `E_WORKTREE_DETACHED`, `E_PATH_OCCUPIED` | the directory-name-equals-branch-name rules below |
| `E_STALE_CONSTITUTION` | blocked by `bin/wt-sync` (see below) |
| `E_INTERRUPTED` | `bin/wt` itself took a Ctrl-C or a `TERM` (during a build, say) |
| `E_SESSION_NONZERO` | the session itself exited non-zero |

A non-zero session exit is ordinary — a Ctrl-C, or a `--shell` whose last
command failed — so it is recorded at `info` level and kept out of the
problem counts, which would otherwise fill up with it. `--logs` reports the
clean/non-zero split on its own `== Sessions ==` line instead; a session
that dies on every start shows there as `0 ended cleanly`.

What the log can and cannot hold: `devcontainer up`'s full output — the
build, the feature installs, `postCreate` — is captured, and that is where
container-start errors actually live. The `claude` session itself is an
interactive TTY, so its stream is deliberately **not** captured (teeing it
would record the whole terminal-UI escape sequence and nothing useful);
what is recorded for the session is its exit status, plus the pre-flight
probes either side of it. Errors from inside a session are in Claude
Code's own transcripts under `~/.claude/projects/`.

Logging is a diagnostic, never a gate — an unwritable log directory
downgrades to no logging rather than refusing to start a session. Set
`WT_LOG_DIR` to write somewhere else, or `WT_NO_LOG=1` to turn it off.
Run transcripts are pruned to the newest 50, and `events.jsonl` is capped
at 5000 lines.

## `postCreateCommand` failure is permanent until `--rebuild`

`.devcontainer/post-create.sh` is what installs `uv` and the Claude Code
CLI *into the container* — they are not in the image. It runs **once**, at
container creation, and its retry loop gives up after three attempts (a
full Docker VM disk has caused exactly that here; see **Docker Desktop
resources** below). The container is still created when it fails, so every
later `bin/wt <branch>` *resumes* it and `postCreate` never runs again.

`bin/wt` now probes for `claude` after bringing the container up and stops
with `E_CLAUDE_MISSING` and the one fix that works, rather than exec'ing
into a container that cannot run it:

```bash
bin/wt <branch> --rebuild
```

## Day to day: starting a chore, fix, docs or perf branch

Same idea, one flag:

```bash
bin/wt chore/tidy-logging --no-container
```

You get `.worktrees/chore/tidy-logging` on branch `chore/tidy-logging`,
branched from `main`, with `claude` running on the host in that
directory. Nothing is built and nothing is stopped on exit — there is no
container in play, so the teardown that stops a spec's container on exit
simply does not apply.

Two things still hold that are easy to assume don't:

- **The wrong-branch guard is still armed.** `bin/wt` exports
  `WORKTREE_CONTAINER=<branch>` into the host session too, which is the
  variable `check-worktree-sync.sh` reads to block an edit whose `HEAD`
  has drifted off the branch the session was started for. Without it that
  guard would be dead on exactly the branches this mode creates.
- **Siblings are reachable, and still off limits.** Every worktree lives
  under the same `.worktrees/` root, so from `.worktrees/chore/foo` a
  sibling is `../bar` or `../../028-some-spec` depending on how deep the
  branch name nests — ordinary paths, with no mount boundary in front of
  them. The `Read(.worktrees/**)` / `Edit(.worktrees/**)` deny rules are
  resolved against the session's own directory, so inside a worktree they
  match nothing at all and are inert. For non-spec work the separation is
  a rule, not a wall — which is exactly why spec work keeps its container
  instead of also moving to the host.

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

Do this yourself — Claude cannot. `.claude/settings.json` denies
`Read(.worktrees/**)` and `Edit(.worktrees/**)`, so a session in the
primary checkout has no more access to a sibling worktree than a session
inside a container does (see **What Claude can and cannot see** below).
Actual merge conflicts, if any, still surface normally at merge/rebase
time regardless.

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

## Pruning merged work

Run from the **primary checkout** (an isolated container cannot see its
siblings, which is the point):

```bash
bin/wt-prune            # dry run: reports what it would remove
bin/wt-prune --yes      # actually remove it
```

For every worktree under `.worktrees/` and every local branch without one,
it removes the worktree, the branch and the devcontainer once GitHub says
that branch's pull request is **merged**.

It asks GitHub rather than git because this repo merges exclusively by
**squash**: a merged branch's tip is never an ancestor of `main`, so
`git branch --merged` and `git merge-base --is-ancestor` report every
merged branch as unmerged. `gh pr list --state merged --head <branch>` is
the only reliable local test.

What it will never do:

- delete anything without `--yes` (dry run is the default);
- touch a worktree with uncommitted or untracked work;
- remove a branch that has **no** PR — that gets reported for you to judge;
- remove a branch whose PR was **closed without merging**, unless you pass
  `--include-closed`.

### Cleaning up orphaned containers

`bin/wt-prune` removes each container alongside its worktree. If a
worktree was removed some other way and left its container behind, sweep
those alone from the primary repo root:

```bash
.specify/scripts/bash/prune-worktree-containers.sh
```

## Checking for stale bootstrap files

`CLAUDE.md`, the constitution, `.claude/settings.json`, the hook scripts,
`bin/` and `.devcontainer/` are all *tracked*, so every worktree holds its
own copy frozen at the moment it was created. A worktree that has not
rebased since is being governed by whatever those files said back then —
issue #293 found four constitution versions live at once, spanning three
major versions.

```bash
bin/wt-sync                     # every worktree
bin/wt-sync <branch>            # just one
bin/wt-sync --ref=origin/main   # compare against something else
```

The rule it enforces:

| drift | result |
|---|---|
| constitution **major**-version gap | **blocks** (exit 2) — `bin/wt` refuses to start that worktree |
| constitution minor/patch, `CLAUDE.md`, settings, skills, hooks, `bin/` | warns |
| `.devcontainer/` changed | warns, and says the fix also needs `bin/wt <branch> --rebuild` |

`bin/wt` runs this itself before bringing a container up, so a worktree
two constitution majors behind cannot quietly start a session. The fix is
always to rebase:

```bash
git -C .worktrees/<branch> rebase origin/main
```

`bin/wt <branch> --allow-stale` overrides the block if you genuinely need
it. Staleness is measured against the **merge base**, so a branch that
deliberately edits `CLAUDE.md` or a hook counts as ahead, not stale.

## Directory name must equal branch name

A worktree for branch `<branch>` lives at `.worktrees/<branch>` — slashes
and all, so `docs/overview` lives at `.worktrees/docs/overview`. The
container label, `WORKTREE_CONTAINER`, the edit guard, `bin/wt-prune` and
`bin/wt-sync` all key off that equality. `bin/wt` now refuses to start a
session where the two have drifted apart (issue #293 found two such cases)
and tells you which `git worktree move` or `git switch` fixes it.

## The primary checkout returns to `main`

Feature work happens in worktrees, so the primary checkout should be
sitting on `main` whenever nobody is using it. Left on the last branch
worked on there, it silently becomes the wrong `--base` for the next
`bin/wt` run.

`.specify/scripts/bash/return-to-main.sh` runs on `SessionEnd` and switches
the primary checkout back to `main` — but only when the tree is clean and
no rebase/merge is in progress; otherwise it says why it left things alone.
On `SessionStart` it only *reports* a non-trunk branch, never switches:
moving HEAD out from under a session that was deliberately put there would
be worse than the drift. It is a no-op inside any worktree or container.

## What Claude can and cannot see

- **Denied**: `Read(.worktrees/**)` and `Edit(.worktrees/**)` in the
  tracked `.claude/settings.json`, so a Claude session in the primary
  checkout cannot read or edit any worktree — the same blindness a
  containerised session has, from the other direction. VS Code is a host
  application and is unaffected, so you keep full visibility.
- **Enforced on every branch**: the `Edit|Write|NotebookEdit` guard
  `check-worktree-sync.sh` compares `WORKTREE_CONTAINER` against `HEAD`.
  It used to exit early whenever `.specify/feature.json` was absent, which
  disabled it for every `chore/*`, `fix/*`, `perf/*` and `issue/*` worktree
  (issue #293, Leak B). It stands down mid-rebase/merge, so it can never
  block the conflict resolution that brings a stale worktree back in line.
- **Known limits**: `Bash` permission rules are prefix matches, so
  `Bash(cd .worktrees:*)` and friends catch the obvious shell paths but not
  every possible one (`cat ./.worktrees/x/y`). And the shared `.git`
  directory lets any container read *committed* content on other branches —
  closing that would break rebasing onto `main`, so it is an accepted limit,
  not an oversight.

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
- `~/.claude.json` → `/home/vscode/.claude.json.host` (**read-only**) — a
  *sibling* file (not inside the `~/.claude` directory), holding the oauth
  account/onboarding state (`oauthAccount`, `hasCompletedOnboarding`, ...).
  Mounting only `~/.claude` and not this file was the original bug: each
  new container got its own empty `~/.claude.json`, so it looked
  authenticated (credentials present) but wasn't, and any container
  recreation forced a fresh login. Both mounts together are what actually
  fixes it — verified 2026-08-31 by force-recreating a container and
  running `claude -p "..."` non-interactively with no login prompt. It's
  mounted read-only, and at `.host` rather than its real path, because of
  the corruption issue below — `restore-claude-config.sh` copies it into
  the container's real `~/.claude.json` on every start.

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

### Recovering from a corrupted or missing `~/.claude.json`

`~/.claude.json` used to be bind-mounted read-write directly at its real
path — a *single-file* bind mount, unlike the directory mounts (`~/.claude`,
`~/.config/gh`). Claude Code saves that file atomically (backup + temp file
+ `rename()` over the real path), and Docker Desktop's virtiofs/osxfs
bind mounts don't reliably carry a `rename()` across a single-file mount
like that. In practice this went beyond the file occasionally looking
*missing* inside a container: because the file was shared read-write
across the host **and every concurrently-running worktree container**, a
save from any one of them could truncate the host's real `~/.claude.json`
to 0 bytes instead of atomically replacing it — corrupting the live config
for every other session sharing it, including the host itself (observed
twice in one evening, 2026-09-02, each time surfacing on the *host* as
`claude` refusing to start with "JSON Parse error: Unexpected EOF").

Fixed by mounting the host file **read-only** at `~/.claude.json.host`
instead of at its real path (`.devcontainer/devcontainer.json`) and having
`.devcontainer/restore-claude-config.sh` copy it into the container's own
real `~/.claude.json` — an ordinary in-container file, not a mount — on
every start (`postStartCommand`, which fires on resume too, not just first
creation). A container can therefore no longer write back through to the
host file at all, so it can't corrupt it. The trade-off: auth/onboarding
state changed *inside* a container (e.g. re-running `claude login` there)
stays local to that container and is overwritten by the host's copy on the
next start — that's fine since the actual OAuth token lives in the
still-read-write, still-shared `~/.claude/.credentials.json`.

If the *host's* `~/.claude.json` itself ever gets corrupted (0 bytes, or a
JSON parse error on `claude` startup), restore it from the newest backup
under `~/.claude/backups/.claude.json.backup.<timestamp>` — that directory
lives inside the `~/.claude` directory mount, so it's visible on the host
too:

```bash
cp "$(ls -t ~/.claude/backups/.claude.json.backup.* | head -1)" ~/.claude.json
```

### Bootstrap noise on container creation

Creating a container used to end with two messages that looked like
failures and were not:

```
Claude configuration file not found at: /home/vscode/.claude.json
A backup file exists at: /home/vscode/.claude/backups/.claude.json.backup.<ts>
...
⚠ Setup notes:
  ● Native installation exists but ~/.local/bin is not in your PATH.
```

Both came from lifecycle ordering, and both are fixed in
`.devcontainer/post-create.sh`:

- The devcontainer lifecycle runs `postCreateCommand` (which installs
  Claude Code) **before** `postStartCommand` (`restore-claude-config.sh`,
  which puts `~/.claude.json` in place), so on a fresh container the
  installer genuinely found no config. Its suggested `cp` from
  `~/.claude/backups/` was actively wrong advice here: that directory
  arrives through the shared `~/.claude` bind mount, so it holds the
  *host's* backups, and `postStartCommand` overwrites the file seconds
  later anyway. `post-create.sh` now runs the restore itself first — it is
  idempotent and still runs again on every start.
- Both installers put their binary in `~/.local/bin`, which is added to
  `PATH` by a snippet in `~/.profile` that is conditional on the directory
  *already existing* — and it does not exist in the base image. So during
  `postCreate` it genuinely was not on `PATH`. `post-create.sh` now creates
  and exports it before installing, which both silences the warning and
  satisfies the `~/.profile` condition for every later login shell — which
  is how `devcontainer exec` resolves `claude`.

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
