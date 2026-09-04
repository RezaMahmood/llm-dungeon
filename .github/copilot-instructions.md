# Copilot instructions

This repository's binding engineering rules live in
`.specify/memory/constitution.md`. When performing a pull request code
review, always use the `repo-constitution-review` agent skill
(`.github/skills/repo-constitution-review/SKILL.md`) in addition to general
review — it covers GitHub- and CI/CD-specific rules (workflow security, PR
title conventions, PII in GitHub artifacts, the AI-agent GitHub handoff
process) that a generic review has no way to know about. It deliberately
does not cover application code, UI, in-progress implementation details, or
files under `specs/**` — spec-kit feature specs/plans/tasks are authored and
reviewed by Claude, not Copilot.
