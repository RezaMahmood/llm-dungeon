# Baseline Metrics (pre-implementation)

Captured 2026-09-01 via `gh run list --workflow=<name>.yml --status=success --limit=5 --json databaseId,createdAt,updatedAt,displayTitle`, for SC-001 ("End-to-end time from merging a backend or frontend change to that change being live in production decreases measurably compared to the current pipeline"). These are the last 5 successful runs of each deploy workflow *before* this feature's restructuring (T007+) landed.

## `backend-deploy.yml`

| Run ID | Started (UTC) | Finished (UTC) | Duration |
|---|---|---|---|
| 33498197984 | 2026-09-01T10:35:31Z | 2026-09-01T10:38:09Z | 2m38s |
| 33438832256 | 2026-08-31T20:57:48Z | 2026-08-31T21:00:22Z | 2m34s |
| 33436552453 | 2026-08-31T20:32:09Z | 2026-08-31T20:34:45Z | 2m36s |
| 33433142899 | 2026-08-31T19:54:52Z | 2026-08-31T19:57:24Z | 2m32s |
| 33428810949 | 2026-08-31T19:07:24Z | 2026-08-31T19:10:00Z | 2m36s |

**Average**: ~2m35s

## `frontend-deploy.yml`

| Run ID | Started (UTC) | Finished (UTC) | Duration |
|---|---|---|---|
| 33498197985 | 2026-09-01T10:35:31Z | 2026-09-01T10:37:04Z | 1m33s |
| 33475263197 | 2026-09-01T05:52:15Z | 2026-09-01T05:53:45Z | 1m30s |
| 33446375982 | 2026-08-31T22:28:32Z | 2026-08-31T22:30:25Z | 1m53s |
| 33445745729 | 2026-08-31T22:20:24Z | 2026-08-31T22:21:49Z | 1m25s |
| 33444320972 | 2026-08-31T22:02:40Z | 2026-08-31T22:04:15Z | 1m35s |

**Average**: ~1m35s

## Comparison (post-implementation, captured 2026-09-01/02)

Post-implementation runs, from real merges during issue #143's sign-off validation:

| Workflow | Run ID | Started (UTC) | Finished (UTC) | Duration |
|---|---|---|---|---|
| `backend-deploy.yml` | 33561515773 | 2026-09-01T21:31:15Z | 2026-09-01T21:34:37Z | 3m22s |
| `backend-deploy.yml` | 33560604798 | 2026-09-01T21:21:18Z | 2026-09-01T21:24:30Z | 3m12s |
| `frontend-deploy.yml` | 33561515633 | 2026-09-01T21:31:15Z | 2026-09-01T21:34:04Z | 2m49s |
| `frontend-deploy.yml` | 33561192762 | 2026-09-01T21:27:49Z | 2026-09-01T21:30:17Z | 2m28s |

| Workflow | Baseline avg | Post-implementation avg | Result |
|---|---|---|---|
| `backend-deploy.yml` | ~2m35s | ~3m17s | **+42s slower — SC-001 NOT MET** |
| `frontend-deploy.yml` | ~1m35s | ~2m38s | **+63s slower — SC-001 NOT MET** |

**Root cause**: splitting one job into `test → release → build → deploy` pays a fresh runner + checkout + toolchain-setup + cache-restore cost at every stage boundary, and `needs:`-chained jobs run strictly sequentially in GitHub Actions — the added overhead is paid 3-4 times per run instead of once, with no eliminated work to offset it (frontend's `test`/`release`/`build` each run their own `npm ci`; backend still pays the exact same unavoidable Azure Oryx remote build it always did — see `spec.md`'s Retrospective and `research.md` decision #1's amendment). This is the motivating finding for the follow-up spec.
