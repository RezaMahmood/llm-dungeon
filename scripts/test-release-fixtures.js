#!/usr/bin/env node
// Version-computation fixture test for specs/023-cicd-pipeline-optimization.
//
// Covers User Story 3 (tasks.md T014) — this is the automated guard
// against the bug /speckit-analyze finding F1 found in the original
// design: gating a component's version bump on the PR title's scope word
// breaks for vertical-slice commits (one commit touching both frontend
// and backend paths). The fix (research.md decision #3) is path-diff
// filtering via `semantic-release-monorepo`'s `onlyPackageCommits`,
// combined with `@semantic-release/commit-analyzer` for the bump type.
// This test exercises that exact combination against synthetic commits
// in a real (temporary) git repository — no network calls, no GitHub
// token needed, so it runs identically locally and in CI.
//
// Run with: node scripts/test-release-fixtures.js

import path from "path";
import fs from "fs";
import { onlyPackageCommits } from "semantic-release-monorepo/src/only-package-commits.js";
import { initGitRepo, gitCommitsWithFiles } from "semantic-release-monorepo/src/git-utils.js";
import { analyzeCommits as commitAnalyzerAnalyzeCommits } from "@semantic-release/commit-analyzer";

let failures = 0;
let passes = 0;

function check(label, condition) {
  if (condition) {
    passes += 1;
    console.log(`  ✓ ${label}`);
  } else {
    failures += 1;
    console.error(`  ✗ ${label}`);
  }
}

const logger = {
  log: () => {},
  error: () => {},
  success: () => {},
  await: () => {},
};

async function analyzeType(commits) {
  if (commits.length === 0) return null;
  return commitAnalyzerAnalyzeCommits({}, { commits, logger, cwd: process.cwd() });
}

async function main() {
  const { cwd } = await initGitRepo(false);
  const originalCwd = process.cwd();
  process.chdir(cwd);

  try {
    fs.mkdirSync(path.join(cwd, "backend"));
    fs.mkdirSync(path.join(cwd, "frontend"));

    // Seed commit: creates both package roots so pkgUp() can find them.
    // Excluded from every scenario below by only ever analyzing the
    // commits created after it.
    await gitCommitsWithFiles([
      {
        message: "chore: seed monorepo package roots",
        files: [
          { name: "backend/package.json", body: '{"name":"backend","version":"0.1.0"}' },
          { name: "frontend/package.json", body: '{"name":"frontend","version":"0.1.0"}' },
        ],
      },
    ]);

    // Fixture commits, in creation order:
    const created = await gitCommitsWithFiles([
      { message: "fix(backend): correct a bug", files: [{ name: "backend/index.js" }] },
      { message: "feat(frontend): add a widget", files: [{ name: "frontend/index.js" }] },
      { message: "chore(backend): tidy comments", files: [{ name: "backend/NOTES.md" }] },
      {
        message: "fix(backend): vertical-slice change touching both packages",
        files: [{ name: "backend/index2.js" }, { name: "frontend/index2.js" }],
      },
    ]);
    // gitCommitsWithFiles returns commits newest-first (git log order);
    // re-derive named handles for readability below.
    const [vertical, chore, feat, fix] = created;

    console.log("Path-diff filtering (semantic-release-monorepo's onlyPackageCommits):");

    process.chdir(path.join(cwd, "backend"));
    const backendCommits = await onlyPackageCommits([fix, feat, chore, vertical]);
    check(
      "backend sees [fix, chore, vertical] and NOT the frontend-only feat",
      backendCommits.length === 3 &&
        backendCommits.some((c) => c.hash === fix.hash) &&
        backendCommits.some((c) => c.hash === chore.hash) &&
        backendCommits.some((c) => c.hash === vertical.hash) &&
        !backendCommits.some((c) => c.hash === feat.hash)
    );

    process.chdir(path.join(cwd, "frontend"));
    const frontendCommits = await onlyPackageCommits([fix, feat, chore, vertical]);
    check(
      "frontend sees [feat, vertical] and NOT the backend-only fix/chore",
      frontendCommits.length === 2 &&
        frontendCommits.some((c) => c.hash === feat.hash) &&
        frontendCommits.some((c) => c.hash === vertical.hash) &&
        !frontendCommits.some((c) => c.hash === fix.hash) &&
        !frontendCommits.some((c) => c.hash === chore.hash)
    );

    console.log("\nBump-type computation (@semantic-release/commit-analyzer) on the filtered sets:");

    const backendBump = await analyzeType(backendCommits);
    check(
      "backend's filtered commits [fix, chore, vertical(fix)] => patch",
      backendBump === "patch"
    );

    const frontendBump = await analyzeType(frontendCommits);
    check(
      "frontend's filtered commits [feat, vertical(fix)] => minor (feat outranks fix)",
      frontendBump === "minor"
    );

    console.log("\nThe F1 regression test — a single vertical-slice commit alone:");

    process.chdir(path.join(cwd, "backend"));
    const backendVerticalOnly = await onlyPackageCommits([vertical]);
    const backendVerticalBump = await analyzeType(backendVerticalOnly);
    check(
      "backend, given ONLY the vertical-slice commit, bumps patch",
      backendVerticalOnly.length === 1 && backendVerticalBump === "patch"
    );

    process.chdir(path.join(cwd, "frontend"));
    const frontendVerticalOnly = await onlyPackageCommits([vertical]);
    const frontendVerticalBump = await analyzeType(frontendVerticalOnly);
    check(
      "frontend, given ONLY the vertical-slice commit (titled fix(backend):...), ALSO bumps patch " +
        "— this is F1's fix: eligibility comes from the diff, not the PR title's declared scope",
      frontendVerticalOnly.length === 1 && frontendVerticalBump === "patch"
    );

    console.log("\nNon-releasable commits produce no bump:");

    process.chdir(path.join(cwd, "backend"));
    const choreOnly = await onlyPackageCommits([chore]);
    const choreBump = await analyzeType(choreOnly);
    check("a lone chore commit yields no version bump", choreBump === null);
  } finally {
    process.chdir(originalCwd);
  }

  console.log(`\n${passes} passed, ${failures} failed`);
  process.exit(failures > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
