const tenantId = import.meta.env.VITE_AZURE_TENANT_ID;
const clientId = import.meta.env.VITE_AZURE_APP_ID;
const redirectUri = import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin + "/";

export const msalConfig = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri,
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
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
