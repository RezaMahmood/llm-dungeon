import axios from "axios";

/**
 * Reads the deployed frontend and backend versions (issue #255). Both are the
 * semantic-release versions GitHub releases under, and both are fetched at
 * runtime rather than baked into the bundle: the two components deploy
 * independently, so a cached bundle carrying a build-time constant would
 * misreport whichever half had moved on.
 */

/** Shown when a version can't be determined (local dev, or an artifact built
 * before its version stamp existed) — never a hardcoded number that goes stale. */
export const UNKNOWN_VERSION = "unknown";

/** Non-empty version string from a response body, else UNKNOWN_VERSION. Guards
 * against a rewrite/fallback handing back HTML instead of the expected JSON. */
function versionFrom(data) {
  return typeof data?.version === "string" && data.version.trim() ? data.version.trim() : UNKNOWN_VERSION;
}

/**
 * The deployed frontend version, from the `version.json` that
 * `_build-frontend.yml` stamps into `dist/` alongside the bundle.
 * `staticwebapp.config.json` excludes `.json` from the SPA navigation
 * fallback, so this resolves to the real file rather than index.html.
 */
export async function getFrontendVersion() {
  const response = await axios.get("/version.json", { headers: { Accept: "application/json" } });
  return versionFrom(response.data);
}

/** The deployed backend version (anonymous `GET /api/version`) — no token, so
 * the badge works on the login screen too. */
export async function getBackendVersion() {
  const response = await axios.get("/api/version");
  return versionFrom(response.data);
}
