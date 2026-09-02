/**
 * Small, standalone constant — added as a trivial validation change for
 * issue #143's CI/CD pipeline sign-off (specs/023-cicd-pipeline-optimization
 * Scenario 1/3). Not wired into any UI; exists only to exercise a real
 * "feat" release for the frontend component.
 *
 * QA note (specs/023-cicd-pipeline-optimization Scenario 2, 2026-09-02):
 * documented with JSDoc to validate frontend-build.yml's build/version/
 * cache-on-merge pipeline for the post-#161 CI/CD design.
 */
export const APP_NAME = "LLM Dungeon Adventure";
