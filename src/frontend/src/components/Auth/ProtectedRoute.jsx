import { InteractionStatus } from "@azure/msal-browser";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { Navigate } from "react-router-dom";

import { useCapabilities } from "../../hooks/useCapabilities.js";
import AuthenticatedLayout from "../Layout/AuthenticatedLayout.jsx";

/**
 * Wraps a route that requires authentication and, optionally, a specific
 * capability. Unauthenticated users are redirected to login; users lacking
 * the required capability see an inline 403 message (not a redirect), per
 * contracts/ui-menu-states.md.
 *
 * Waits for MSAL to finish reading its cached session (`inProgress`) before
 * judging `isAuthenticated` — otherwise a hard browser reload can catch MSAL
 * mid-initialization and momentarily report a valid session as unauthenticated,
 * bouncing the user to /login (contracts/reload-resilience.md Guarantee 2,
 * FR-007/FR-009).
 */
export function ProtectedRoute({ capability, children }) {
  const { inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { hasPlayer, hasAdministrator, loading } = useCapabilities();

  if (inProgress !== InteractionStatus.None) {
    return <div>Loading…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return <div>Loading…</div>;
  }

  const capabilityMap = { Player: hasPlayer, Administrator: hasAdministrator };
  if (capability && !capabilityMap[capability]) {
    return (
      <AuthenticatedLayout>
        <div role="alert" style={{ padding: "var(--space-6)" }}>
          Access not granted
        </div>
      </AuthenticatedLayout>
    );
  }

  return <AuthenticatedLayout>{children}</AuthenticatedLayout>;
}

export default ProtectedRoute;
