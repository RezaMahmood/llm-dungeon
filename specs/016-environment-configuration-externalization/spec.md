# Feature Specification: Environment Configuration Externalization

**Feature Branch**: `016-environment-configuration-externalization`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Split out of `007-azure-infrastructure-provisioning` on 2026-08-29, so that spec covers at most two user stories. This spec covers the fifth user story originally specified there — "Environment Configuration Is Externalized, Not Hardcoded".

**Split**: This spec depends on the Deployment Environment and GitHub Actions Workflow provisioned/defined in `007-azure-infrastructure-provisioning`; it adds no new infrastructure, only the requirement that configuration values are read from environment-scoped sources rather than hardcoded.

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are the engineering team; the value delivered is that the same
  workflow and application code stay portable across environments without a code change.
-->

### User Story 1 - Environment Configuration Is Externalized, Not Hardcoded (Priority: P1)

Azure resource names needed by GitHub Actions workflows come from GitHub environment variables scoped to the target environment, and application configuration values consumed by the backend come from the Function App's application settings — neither is hardcoded into workflow files or application code, and no additional configuration service is introduced.

**Why this priority**: This keeps the same workflow and application code portable across environments without code changes; it is the sole focus of this spec.

**Independent Test**: Verify the GitHub Actions workflow reads Azure resource names from the GitHub environment's variables rather than a hardcoded value in the workflow file; separately, change an application setting for the backend and verify the running application picks it up without a code change or redeploy.

**Acceptance Scenarios**:

1. **Given** a GitHub Actions workflow that needs an Azure resource name, **When** it runs, **Then** it reads that name from the GitHub environment's variables rather than a value hardcoded in the workflow file.
2. **Given** the backend needs an application configuration value, **When** it reads that value, **Then** it comes from the Function App's application settings, with no Azure App Configuration service or Key Vault involved.

---

### Edge Cases

- A required application setting is missing for a given environment: the backend fails fast with a clear startup error identifying the missing setting, rather than failing unpredictably at first use.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Application configuration values consumed by the backend MUST be provided via the Function App's application settings; no Azure App Configuration service or Key Vault is provisioned or required for this purpose.
- **FR-002**: Azure resource names needed by GitHub Actions workflows MUST be supplied via GitHub environment variables scoped to the target deployment environment (see `007-azure-infrastructure-provisioning`), not hardcoded in workflow files.
- **FR-003**: A required application setting that is missing at backend startup MUST cause a clear, immediate startup failure identifying the missing setting, rather than an unpredictable failure at first use.
- **FR-004**: Each distinct configuration outcome (GitHub Actions workflow reading a resource name from environment variables, backend reading an application setting, and fail-fast startup on a missing required setting) MUST have a corresponding automated check verifying its expected behavior.

### Key Entities

- **Deployment Environment**: Defined in `007-azure-infrastructure-provisioning`; this spec specifies only that its GitHub environment variables and the Function App's application settings are the sole source of environment-specific configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Changing an application configuration value for a given environment requires an application-settings update only — no application code change and no code redeployment.

## Assumptions

- No additional configuration service (Azure App Configuration, Key Vault) is introduced by this spec; application settings and GitHub environment variables are treated as sufficient at this project's scale, consistent with `007-azure-infrastructure-provisioning`'s "no need for azure configuration service or key vault" input.
