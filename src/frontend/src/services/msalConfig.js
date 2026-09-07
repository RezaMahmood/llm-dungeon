const tenantId = import.meta.env.VITE_AZURE_TENANT_ID;
const clientId = import.meta.env.VITE_AZURE_APP_ID;
// MSAL v5 requires a dedicated "redirect bridge" page (redirect.html) rather
// than the app's own index page: Entra ID sends Cross-Origin-Opener-Policy
// headers, so MSAL can no longer read the popup/iframe's location directly
// and instead relies on that page calling broadcastResponseToMainFrame() to
// hand the auth response back over the BroadcastChannel API. Pointing this at
// "/" (the full SPA) leaves that call never made, which breaks loginPopup/
// acquireTokenSilent and surfaces as a Cross-Origin Read Blocking (CORB)
// warning in devtools. See https://aka.ms/msaljs/redirect-bridge.
const redirectUri = import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin + "/redirect.html";

export const msalConfig = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri,
  },
  cache: {
    // MSAL v4+ encrypts localStorage entries with a session-scoped key, so
    // this buys a fast in-tab reload rather than persistence across browser
    // restarts. `storeAuthStateInCookie` was dropped from CacheOptions in
    // msal-browser v5 and is no longer set here.
    cacheLocation: "localStorage",
  },
};

export const loginRequest = {
  // openid/profile/email alone leave MSAL with no resource scope to request,
  // so Azure AD defaults the access token's audience to Microsoft Graph
  // instead of this app — the backend validates audience against its own
  // AZURE_APP_ID and always rejected it. access_as_user (exposed on this app
  // registration) makes the access token audience this app itself.
  scopes: ["openid", "profile", "email", `api://${clientId}/access_as_user`],
};
