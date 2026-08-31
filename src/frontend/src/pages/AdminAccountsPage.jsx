import { useMsal } from "@azure/msal-react";
import { useCallback, useState } from "react";

import AccountForm from "../components/Admin/AccountForm.jsx";
import AccountList from "../components/Admin/AccountList.jsx";
import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { useRefreshable } from "../hooks/useRefreshable.js";
import { listAccounts } from "../services/accountService.js";
import { loginRequest } from "../services/msalConfig.js";

export function AdminAccountsPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const { user } = useAuth();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);

  const fetchAccounts = useCallback(async () => {
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    setToken(tokenResponse.accessToken);
    const data = await listAccounts(tokenResponse.accessToken);
    return data.accounts || [];
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  const { data: accounts, loading, error, refresh } = useRefreshable(fetchAccounts);
  usePublishRefresh({ refresh, loading });

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1 style={{ margin: 0 }}>People</h1>
      <hr className="hr" />
      <AccountForm token={token} onAdded={refresh} />
      <hr className="hr" />
      {error && (
        <p role="alert" className="text-muted">
          Couldn&rsquo;t refresh the account list. Showing the last loaded results.
        </p>
      )}
      {loading && !accounts ? (
        <p className="text-muted">Loading accounts…</p>
      ) : (
        <AccountList
          accounts={accounts || []}
          token={token}
          currentUserEmail={user?.email}
          onRemoved={refresh}
        />
      )}
    </div>
  );
}

export default AdminAccountsPage;
