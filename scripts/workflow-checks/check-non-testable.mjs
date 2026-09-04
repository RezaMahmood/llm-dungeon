#!/usr/bin/env node
// Single source of truth for "does this changed-file set count as
// non-testable-only" (FR-019/FR-020, specs/023-cicd-pipeline-optimization).
//
// .github/actions/detect-non-testable-changes/action.yml previously tried
// to compute this via dorny/paths-filter's predicate-quantifier: "every",
// which actually means "true if ANY changed file matches ALL of the given
// patterns" — not "every changed file matches AT LEAST ONE pattern", which
// is what FR-019 needs. Neither of dorny/paths-filter's two quantifier
// modes expresses a for-all-files/exists-a-matching-pattern predicate, so
// against a multi-pattern OR-style list like the one below, `every` always
// evaluated false in practice — docs-only changes never actually skipped
// (see #165 Scenario 6 live validation). This module is the real
// implementation, imported by both the composite action (via the CLI mode
// below) and test-non-testable-detection.js's fixture tests, so the two
// can never drift out of sync the way the inline dorny/paths-filter config
// and this file's earlier standalone reimplementation once did.

import mm from "micromatch";

export const NON_TESTABLE_PATTERNS = [
  "**/*.md",
  "specs/**",
  "docs/**",
  "LICENSE",
  "LICENSE.*",
  "CONTRIBUTING.md",
];

export function allNonTestable(changedFiles) {
  return changedFiles.every((f) => mm.isMatch(f, NON_TESTABLE_PATTERNS, { dot: true }));
}

// CLI mode: prints "true"/"false" for a JSON array of changed file paths,
// taken from the first argv or the CHANGED_FILES_JSON env var.
if (import.meta.url === `file://${process.argv[1]}`) {
  const raw = process.argv[2] ?? process.env.CHANGED_FILES_JSON ?? "[]";
  const files = JSON.parse(raw);
  console.log(allNonTestable(files) ? "true" : "false");
}
