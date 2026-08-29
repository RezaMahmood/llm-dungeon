const ROLE_TAG_CLASS = {
  Administrator: "tag tag-accent",
  Player: "tag tag-neutral",
};

export function AccountList({ accounts = [] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Email</th>
          <th>Roles</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {accounts.map((account) => (
          <tr key={account.email}>
            <td>{account.email}</td>
            <td>
              {account.roles.map((role) => (
                <span key={role} className={ROLE_TAG_CLASS[role] || "tag tag-neutral"}>
                  {role}
                </span>
              ))}
            </td>
            <td>{account.bound ? "Signed in" : "Not yet signed in"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default AccountList;
