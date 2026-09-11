import { memo, useCallback, useState } from "react";

import { removeAccount } from "../../services/accountService.js";

const ROLE_TAG_CLASS = {
  Administrator: "tag tag-accent",
  Player: "tag tag-neutral",
};

// Memoized and given a stable `onSelectRemove` so opening/closing the removal-confirm
// dialog for one row (a `pendingEmail`/`status` state change in the parent) doesn't
// re-render every other row in the table — only the affected row's props actually change.
const AccountRow = memo(function AccountRow({ account, isRemovable, onSelectRemove }) {
  return (
    <tr>
      <td>{account.email}</td>
      <td>
        {account.roles.map((role) => (
          <span key={role} className={ROLE_TAG_CLASS[role] || "tag tag-neutral"}>
            {role}
          </span>
        ))}
      </td>
      <td>{account.bound ? "Signed in" : "Pending first sign-in"}</td>
      <td>
        {isRemovable && (
          <button type="button" className="btn btn-ghost" onClick={() => onSelectRemove(account.email)}>
            Remove
          </button>
        )}
      </td>
    </tr>
  );
});

export function AccountList({ accounts = [], token, currentUserEmail, onRemoved }) {
  const [pendingEmail, setPendingEmail] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | removing | error

  const normalizedCurrentUserEmail = (currentUserEmail || "").toLowerCase();

  const handleSelectRemove = useCallback((email) => {
    setStatus("idle");
    setPendingEmail(email);
  }, []);

  const handleConfirmRemove = async () => {
    setStatus("removing");
    try {
      await removeAccount(token, pendingEmail);
      setStatus("idle");
      setPendingEmail(null);
      onRemoved?.(pendingEmail);
    } catch {
      setStatus("error");
    }
  };

  return (
    <>
      <table className="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Roles</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => {
            const isSelf = account.email.toLowerCase() === normalizedCurrentUserEmail;
            const isRemovable = !isSelf && !account.isSeedAdmin;
            return (
              <AccountRow
                key={account.email}
                account={account}
                isRemovable={isRemovable}
                onSelectRemove={handleSelectRemove}
              />
            );
          })}
        </tbody>
      </table>

      {pendingEmail && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true">
            <div className="dialog-title">Remove {pendingEmail}?</div>
            <div className="dialog-body">
              They lose access at their next sign-in. This cannot be undone from here.
            </div>
            {status === "error" && (
              <div role="alert" className="text-muted">
                Could not remove this account. Please try again.
              </div>
            )}
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setPendingEmail(null)}
                disabled={status === "removing"}
              >
                Keep it
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleConfirmRemove}
                disabled={status === "removing"}
              >
                {status === "removing" ? "Removing…" : "Remove account"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default AccountList;
