import { useMsal } from "@azure/msal-react";
import { useCallback, useState } from "react";

import "../components/Admin/AdminAccounts.css";
import AccountForm from "../components/Admin/AccountForm.jsx";
import AccountList from "../components/Admin/AccountList.jsx";
import { usePublishRefresh } from "../context/RefreshContext.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { useRefreshable } from "../hooks/useRefreshable.js";
import { listAccounts } from "../services/accountService.js";
import { loginRequest } from "../services/msalConfig.js";
import PendingIndicator from "../components/Common/PendingIndicator.jsx";

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

  // Never states a count before the first successful load — accounts is null until
  // then (useRefreshable), and stays null through a failed first load too, so a bare
  // "?? 0" would misreport "0 accounts" while still loading or after a failure
  // (code-review finding).
  const heading = accounts === null ? "People" : `${accounts.length} accounts in LLM Dungeon`;

  return (
    <div className="people-shell">
      <div className="people-header">
        <div className="people-kicker">People</div>
        <h2 className="people-heading">{heading}</h2>
        <hr className="hr" style={{ margin: "20px 0 32px" }} />
      </div>
      <div className="people-scroll">
        {error && (
          <p role="alert" className="text-muted">
            Couldn&rsquo;t refresh the account list. Showing the last loaded results.
          </p>
        )}
        {loading && !accounts ? (
          <PendingIndicator>Loading accounts…</PendingIndicator>
        ) : (
          <div className="people-grid">
            <AccountList
              accounts={accounts || []}
              token={token}
              currentUserEmail={user?.email}
              onRemoved={refresh}
            />
            <AccountForm token={token} onAdded={refresh} />
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminAccountsPage;
