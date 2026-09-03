// Shared source of truth for the PR-title format this repo enforces
// (specs/023-cicd-pipeline-optimization FR-011/FR-012, User Story 4).
// Both the required check (.github/workflows/pr-title-check.yml, via
// amannn/action-semantic-pull-request's `types`/`scopes`/`requireScope`
// inputs) and this file's own unit test (test-pr-title.js) are built from
// these same lists, so they can never drift apart silently.

export const TYPES = [
  "feat",
  "fix",
  "chore",
  "docs",
  "refactor",
  "perf",
  "test",
  "build",
  "ci",
  "style",
  "revert",
];

// "frontend"/"backend" are the two versioned components (FR-007); the
// others cover housekeeping/infra changes that still need a format-valid,
// descriptive PR title even though they never gate a version bump (FR-013,
// FR-014). Matches this repo's actual historical scope usage (e.g.
// "chore(deps-dev): ...", "chore(specs): ...").
export const SCOPES = [
  "frontend",
  "backend",
  "infra",
  "devcontainer",
  "ci",
  "specs",
  "deps",
  "deps-dev",
  "docs",
];

const TYPE_PATTERN = TYPES.join("|");
const SCOPE_PATTERN = SCOPES.join("|");

// Accept either:
//   1) type(scope): description
//   2) type/scope description (legacy bot-generated slash style)
//
// Scope is always required in both forms (matching FR-011's "at least the
// type of change and a primary component/area").
export const PR_TITLE_PATTERN = new RegExp(
  `^(?:` +
    `(${TYPE_PATTERN})\\((${SCOPE_PATTERN})\\)(!)?: .+` +
    `|` +
    `(${TYPE_PATTERN})\\/(${SCOPE_PATTERN}) .+` +
  `)$`
);

export function validatePrTitle(title) {
  return PR_TITLE_PATTERN.test(title);
}
