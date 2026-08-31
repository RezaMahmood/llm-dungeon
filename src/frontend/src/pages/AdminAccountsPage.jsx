import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";

import AccountForm from "../components/Admin/AccountForm.jsx";
import AccountList from "../components/Admin/AccountList.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { listAccounts } from "../services/accountService.js";
import { loginRequest } from "../services/msalConfig.js";

export function AdminAccountsPage() {
  const { instance, accounts: msalAccounts } = useMsal();
  const { user } = useAuth();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
    setToken(tokenResponse.accessToken);
    const data = await listAccounts(tokenResponse.accessToken);
    setAccounts(data.accounts || []);
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <h1 style={{ margin: 0 }}>People</h1>
      <hr className="hr" />
      <AccountForm token={token} onAdded={refresh} />
      <hr className="hr" />
      {loading ? (
        <p className="text-muted">Loading accounts…</p>
      ) : (
        <AccountList accounts={accounts} token={token} currentUserEmail={user?.email} onRemoved={refresh} />
      )}
    </div>
  );
}

export default AdminAccountsPage;
