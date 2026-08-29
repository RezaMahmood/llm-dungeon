# Frontend — LLM Dungeon Adventure

ReactJS single-page application implementing sign-in (via MSAL / Microsoft
Entra ID) and the capability-based main menu (feature
`002-login-and-access-control`).

## Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Login/    # LoginScreen, AccessDeniedScreen
│   │   ├── Menu/      # MainMenu, GameMenuItem, AdminMenuItem
│   │   ├── Auth/      # AuthProvider (MSAL context), ProtectedRoute
│   │   └── Common/    # ErrorBoundary
│   ├── services/      # msalConfig, authService, tokenInterceptor
│   ├── hooks/         # useAuth, useCapabilities
│   ├── pages/         # AdminPage, GamePage placeholders
│   └── styles/        # designTokens.css (vendored from specs/designs/styles.css)
```

## Setup

```bash
npm install
cp .env.example .env   # fill in VITE_AZURE_TENANT_ID, VITE_AZURE_APP_ID, VITE_AZURE_REDIRECT_URI
```

## Running locally

```bash
npm run dev
```

Serves at http://localhost:5173.

## Running tests

```bash
npm test
```

Uses Vitest + React Testing Library; MSAL and network calls are mocked.

## Architecture

- **MSAL** (`@azure/msal-react`) handles the Entra ID sign-in flow (popup) and
  token cache/refresh.
- **AuthProvider** wraps the app in `<MsalProvider>`.
- **useAuth** exposes the signed-in user's identity (oid, email).
- **useCapabilities** calls `GET /api/auth/me` and exposes `hasPlayer` /
  `hasAdministrator`.
- **ProtectedRoute** gates routes on authentication and, optionally, a
  specific capability — server-side enforcement at the destination endpoint
  is still required (see [contracts/ui-menu-states.md](../specs/002-login-and-access-control/contracts/ui-menu-states.md)).

## Deployment

Deployed to the Azure Static Web App provisioned by
[007-azure-infrastructure-provisioning](../specs/007-azure-infrastructure-provisioning/spec.md)
via the GitHub Actions workflow, on merge to `main`.

## References

- [contracts/ui-login-screen.md](../specs/002-login-and-access-control/contracts/ui-login-screen.md)
- [contracts/ui-menu-states.md](../specs/002-login-and-access-control/contracts/ui-menu-states.md)
