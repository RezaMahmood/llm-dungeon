import { useMsal } from "@azure/msal-react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { loginRequest } from "../services/msalConfig.js";
import { getStoryConfiguration } from "../services/storyDraftService.js";

/**
 * A story's complete configuration file, read-only, byte-for-byte what the Download
 * action saves (FR-002, FR-004). Unstyled per FR-012's recorded exception — built only
 * from existing design-system classes and token-based styles (plan.md → Constraints).
 */
export function AdminStoryConfigurationPage() {
  const { storyId } = useParams();
  const { instance, accounts: msalAccounts } = useMsal();
  const account = msalAccounts[0];
  const accountKey = account?.homeAccountId ?? account?.username ?? null;

  const [token, setToken] = useState(null);
  const [configurationText, setConfigurationText] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      setToken(tokenResponse.accessToken);
      const text = await getStoryConfiguration(tokenResponse.accessToken, storyId);
      setConfigurationText(text);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- accountKey is the stable dependency
  }, [instance, accountKey, storyId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDownload = () => {
    if (configurationText == null) return;
    const blob = new Blob([configurationText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `story-${storyId}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: "var(--space-4)",
        }}
      >
        <h1 style={{ margin: 0 }}>Story configuration</h1>
        <button
          type="button"
          className="btn btn-primary"
          disabled={configurationText == null}
          onClick={handleDownload}
        >
          Download
        </button>
      </div>
      <hr className="hr" />

      {loading && <p className="text-muted">Loading configuration…</p>}

      {!loading && error && (
        <div>
          <p role="alert">Something went wrong. Please try again.</p>
          <button type="button" className="btn btn-secondary" onClick={load}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && configurationText != null && (
        <div
          role="region"
          aria-label="Story configuration file"
          tabIndex={0}
          style={{
            overflow: "auto",
            maxHeight: "70vh",
            border: "1px solid var(--color-divider)",
            padding: "var(--space-4)",
          }}
        >
          <pre style={{ margin: 0, whiteSpace: "pre" }}>{configurationText}</pre>
        </div>
      )}
    </div>
  );
}

export default AdminStoryConfigurationPage;
