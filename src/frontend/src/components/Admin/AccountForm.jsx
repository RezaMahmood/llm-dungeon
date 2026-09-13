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
    <div className="people-add-panel">
      <div className="ovnum">+</div>
      <h3>Add someone</h3>
      <p className="people-add-intro text-muted">
        They sign in with their school Microsoft account — no password is set here.
      </p>
      <form className="people-add-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="account-email">Microsoft account</label>
          <input
            id="account-email"
            className="input"
            type="text"
            placeholder="ada.bell@school.internal"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>
        <div className="field">
          <label>Roles — choose one or both</label>
          {/* Wrapped so the design system's `.field > label { display: block }` rule
              (designTokens.css) doesn't win over `.people-role-option`'s flex layout —
              matches the canonical mockup's own wrapping div. */}
          <div className="people-role-options">
            <label className="people-role-option">
              <input
                type="checkbox"
                checked={hasPlayer}
                onChange={(event) => setHasPlayer(event.target.checked)}
              />
              <span>
                <span className="people-role-label">Player</span>
                <div className="people-role-description text-muted">
                  Sees only the stories assigned to their class.
                </div>
              </span>
            </label>
            <label className="people-role-option">
              <input
                type="checkbox"
                checked={hasAdministrator}
                onChange={(event) => setHasAdministrator(event.target.checked)}
              />
              <span>
                <span className="people-role-label">Administrator</span>
                <div className="people-role-description text-muted">
                  Creates and edits stories, adds and removes accounts.
                </div>
              </span>
            </label>
          </div>
          <p className="people-role-note text-muted">
            An account can hold both roles. You can grant the other role at any time.
          </p>
        </div>
        <hr className="hr" />
        <button type="submit" className="btn btn-primary btn-block" disabled={status === "submitting"}>
          {status === "submitting" ? "Adding…" : "Add account"}
        </button>
        {status === "error" && (
          <div role="alert" className="text-muted">
            {message}
          </div>
        )}
      </form>
    </div>
  );
}

export default AccountForm;
