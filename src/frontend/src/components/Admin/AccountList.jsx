import { memo, useCallback, useState } from "react";

import { removeAccount } from "../../services/accountService.js";

// Player -> tag-outline, Administrator -> tag-accent (05-admin-users-spec.md §6;
// research.md Decision 5, 030-people-admin-design-spec).
const ROLE_TAG_CLASS = {
  Administrator: "tag tag-accent",
  Player: "tag tag-outline",
};

// Short, locale-aware date (e.g. "12 Aug"), mirroring AdminPage.jsx's formatLastPublished
// pattern. Renders nothing — never a placeholder — when dateAdded is absent.
function formatDateAdded(iso) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

// Two honest sign-in states only (030-people-admin-design-spec Scope note / D3): the
// backend can tell "has bound at least once" from "never bound", but has no live
// session/presence signal, so a third "Signed out · {relative time}" state is never
// rendered — that would claim information the system doesn't have.
function StatusCell({ bound }) {
  return bound ? (
    <span className="status status-on">
      <span className="dot" />
      Signed in
    </span>
  ) : (
    <span className="status status-off">
      <span className="dot" />
      Never signed in
    </span>
  );
}

// Memoized and given a stable `onSelectRemove` so opening/closing the removal-confirm
// dialog for one row (a `pendingEmail`/`status` state change in the parent) doesn't
// re-render every other row in the table — only the affected row's props actually change.
const AccountRow = memo(function AccountRow({ account, isRemovable, onSelectRemove }) {
  const added = formatDateAdded(account.dateAdded);

  return (
    <tr>
      <td className="people-account-cell">{account.email}</td>
      <td>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {account.roles.map((role) => (
            <span key={role} className={ROLE_TAG_CLASS[role] || "tag tag-outline"}>
              {role}
            </span>
          ))}
        </div>
      </td>
      <td>
        <StatusCell bound={account.bound} />
      </td>
      <td className="text-muted">{added}</td>
      <td style={{ width: "1%", whiteSpace: "nowrap" }}>
        {isRemovable && (
          <button
            type="button"
            className="btn btn-ghost"
            style={{ padding: "6px 10px", fontSize: "12px" }}
            onClick={() => onSelectRemove(account.email)}
          >
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
      <div className="people-table-label">All accounts</div>
      <table className="table" style={{ marginTop: "10px" }}>
        <thead>
          <tr>
            <th>Microsoft account</th>
            <th>Role</th>
            <th>Status</th>
            <th>Added</th>
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
      <p className="people-caption text-muted">
        Removing an account revokes access at the next sign-in. Stories the player has finished
        stay in the class record.
      </p>

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
