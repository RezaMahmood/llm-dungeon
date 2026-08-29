import { useMsal } from "@azure/msal-react";

import "./LoginScreen.css";

export function AccessDeniedScreen() {
  const { instance } = useMsal();

  const handleTryAgain = () => {
    instance.logoutRedirect();
  };

  return (
    <div className="login-screen" style={{ alignItems: "center", textAlign: "center" }} role="alert">
      <h1>Access Not Granted</h1>
      <p>
        This account does not have access to LLM Dungeon Adventure. If you believe this is an
        error, please contact your administrator.
      </p>
      <button type="button" className="btn btn-primary" onClick={handleTryAgain}>
        Sign in with a different account
      </button>
    </div>
  );
}

export default AccessDeniedScreen;
