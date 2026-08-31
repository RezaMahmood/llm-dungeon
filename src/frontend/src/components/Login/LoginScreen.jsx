import { useMsal } from "@azure/msal-react";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { loginRequest } from "../../services/msalConfig.js";
import "./LoginScreen.css";

const MESSAGES = {
  cancelled: "Sign in was cancelled. Please try again.",
  failed: "Sign in failed. Please check your connection and try again.",
  sessionExpired: "Your session ended — please sign in again.",
};

export function LoginScreen() {
  const { instance } = useMsal();
  const navigate = useNavigate();
  const location = useLocation();
  const sessionExpired = location.state?.reason === "session-expired";
  const [status, setStatus] = useState(sessionExpired ? "sessionExpired" : "idle"); // idle | loading | cancelled | failed | sessionExpired
  const [message, setMessage] = useState(sessionExpired ? MESSAGES.sessionExpired : "");

  const handleSignIn = async () => {
    setStatus("loading");
    setMessage("");
    try {
      await instance.loginPopup(loginRequest);
      navigate("/menu");
    } catch (err) {
      if (err.errorCode === "user_cancelled" || err.errorCode === "user_cancelled_login") {
        setStatus("cancelled");
        setMessage(MESSAGES.cancelled);
      } else {
        setStatus("failed");
        setMessage(MESSAGES.failed);
      }
    }
  };

  return (
    <div className="login-screen">
      <h1>LLM Dungeon Adventure</h1>
      <p className="text-muted">Sign in to continue</p>
      <hr className="hr" />
      <button
        type="button"
        className="btn btn-primary btn-block"
        onClick={handleSignIn}
        disabled={status === "loading"}
      >
        {status === "loading" ? "Redirecting to Microsoft…" : "Sign in with Microsoft"}
      </button>
      {(status === "cancelled" || status === "failed" || status === "sessionExpired") && (
        <div role="alert" className="login-error">
          {message}
        </div>
      )}
    </div>
  );
}

export default LoginScreen;
