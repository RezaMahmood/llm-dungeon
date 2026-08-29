import { useState } from "react";

import { addAccount } from "../../services/accountService.js";

const MESSAGES = {
  role_required: "Select at least one role (Player and/or Administrator).",
  invalid_email: "Enter a valid email address.",
  default: "Could not add this account. Please try again.",
};

export function AccountForm({ token, onAdded }) {
  const [email, setEmail] = useState("");
  const [hasPlayer, setHasPlayer] = useState(false);
  const [hasAdministrator, setHasAdministrator] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | submitting | error
  const [message, setMessage] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("submitting");
    setMessage("");

    const roles = [
      ...(hasPlayer ? ["Player"] : []),
      ...(hasAdministrator ? ["Administrator"] : []),
    ];

    try {
      const data = await addAccount(token, email, roles);
      setStatus("idle");
      setEmail("");
      setHasPlayer(false);
      setHasAdministrator(false);
      onAdded?.(data.account);
    } catch (err) {
      const code = err.response?.data?.error;
      setStatus("error");
      setMessage(MESSAGES[code] || MESSAGES.default);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="account-email">Email</label>
        <input
          id="account-email"
          className="input"
          type="text"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>
      <div className="field">
        <label>Roles</label>
        <div className="seg">
          <label className="seg-opt">
            <input
              type="checkbox"
              checked={hasPlayer}
              onChange={(event) => setHasPlayer(event.target.checked)}
            />
            <span>Player</span>
          </label>
          <label className="seg-opt">
            <input
              type="checkbox"
              checked={hasAdministrator}
              onChange={(event) => setHasAdministrator(event.target.checked)}
            />
            <span>Administrator</span>
          </label>
        </div>
      </div>
      <button type="submit" className="btn btn-primary" disabled={status === "submitting"}>
        {status === "submitting" ? "Adding…" : "Add account"}
      </button>
      {status === "error" && (
        <div role="alert" className="text-muted">
          {message}
        </div>
      )}
    </form>
  );
}

export default AccountForm;
