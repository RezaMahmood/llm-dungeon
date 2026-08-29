import { useMsal } from "@azure/msal-react";

/**
 * Exposes the signed-in user's identity (oid, email) from the active MSAL account.
 */
export function useAuth() {
  const { accounts } = useMsal();
  const account = accounts[0];

  if (!account) {
    return { user: null, isAuthenticated: false };
  }

  return {
    user: {
      oid: account.idTokenClaims?.oid ?? account.localAccountId,
      email: account.username,
    },
    isAuthenticated: true,
  };
}

export default useAuth;
