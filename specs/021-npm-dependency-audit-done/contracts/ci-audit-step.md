# Contract: CI `npm audit` step

This feature's only external-facing "interface" is the CI contract between a pull request
and the `frontend-test` job in `.github/workflows/test.yml`, and the on-demand command a
maintainer can run locally. Both MUST invoke the same underlying check (FR-010).

## CI step (added to the existing `frontend-test` job, after `npm install`)

```yaml
      - name: Run dependency vulnerability audit
        if: steps.check.outputs.exists == 'true'
        run: npm run audit:frontend
```

Where `src/frontend/package.json` gains:

```json
"scripts": {
  "audit:frontend": "npm audit --audit-level=high"
}
```

(Naming avoids colliding with the reserved `npm audit` command name.)

## Behavior contract

| Input | Output | Effect on PR |
|---|---|---|
| No vulnerability at High/Critical severity | `npm audit --audit-level=high` exits `0` | Step passes; job continues; PR mergeable (subject to other gates) — FR-003 scenario 3 |
| ≥1 vulnerability at High or Critical severity | exits non-zero | Step fails; job fails; PR blocked from merge (existing branch-protection on `frontend-test`) — FR-003 scenario 2 |
| Any vulnerability (any severity) | `npm audit` (default text output, run as part of the same step, not exit-gated) prints package name, installed version range, severity, and fixed version (if any) to the job log | Report visible to maintainers on the PR's checks tab — FR-004, FR-001 scenario 1 |

## Critical-finding issue-creation step (added to `frontend-test`, after the audit steps above)

Requires the workflow job to declare:

```yaml
permissions:
  contents: read
  issues: write
```

```yaml
      - name: Open high-priority issue for Critical findings
        if: steps.check.outputs.exists == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -e
          npm audit --json > audit-report.json || true
          jq -r '.vulnerabilities | to_entries[] | select(.value.severity=="critical") | .key' \
            audit-report.json | while read -r pkg; do
            title="[dependency-audit] Critical: ${pkg}"
            existing=$(gh issue list --state open --search "\"${title}\" in:title" --json number --jq '.[0].number')
            if [ -z "$existing" ]; then
              fixed=$(jq -r --arg p "$pkg" '.vulnerabilities[$p].fixAvailable.version // "none"' audit-report.json)
              range=$(jq -r --arg p "$pkg" '.vulnerabilities[$p].range' audit-report.json)
              gh issue create --title "$title" \
                --label "priority: high" --label "bug" \
                --body "Package: ${pkg}\nInstalled/affected range: ${range}\nSeverity: critical\nFixed version: ${fixed}\n\nDetected by the frontend dependency audit CI step. See \`npm audit\` output on this run for full detail."
            fi
          done
```

| Input | Output | Effect |
|---|---|---|
| A Critical finding with no existing open tracking issue | `gh issue list --search` returns empty | `gh issue create` opens a new issue, labeled `priority: high` + `bug` — FR-011, SC-006 |
| A Critical finding with an existing open tracking issue (same title) | `gh issue list --search` returns that issue's number | No new issue created — FR-011 dedupe, Acceptance Scenario 5 |
| No Critical findings | loop body never executes | No issue created |

## On-demand invocation (FR-010)

```bash
cd src/frontend
npm run audit:frontend      # same pass/fail semantics as CI
npm audit                   # full human-readable report, all severities
npm audit --json            # full machine-readable report, all severities
```

## Dependabot contract (`.github/dependabot.yml`)

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/src/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

| Trigger | Dependabot behavior | Visibility (FR-009) |
|---|---|---|
| New disclosed vulnerability in a monitored package | Dependabot security update PR (independent of the weekly schedule — security PRs open promptly) | Repository "Security" tab (Dependabot alerts) + a PR against `main` |
| New non-security version available | Weekly-scheduled version-update PR | Pull requests list, authored by `dependabot[bot]` |
