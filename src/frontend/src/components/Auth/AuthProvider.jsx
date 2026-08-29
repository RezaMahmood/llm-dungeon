import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import React from "react";

import { msalConfig } from "../../services/msalConfig.js";

export const msalInstance = new PublicClientApplication(msalConfig);

export function AuthProvider({ children }) {
  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
}

export default AuthProvider;
