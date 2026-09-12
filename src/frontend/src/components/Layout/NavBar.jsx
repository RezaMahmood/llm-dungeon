import { useMsal } from "@azure/msal-react";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { useRefreshContext } from "../../context/RefreshContext.jsx";
import { useCapabilities } from "../../hooks/useCapabilities.js";
import { listSavedGames, saveCheckpoint } from "../../services/gameService.js";
import { loginRequest } from "../../services/msalConfig.js";
import RefreshButton from "../Common/RefreshButton.jsx";
import LogoutSavePrompt from "./LogoutSavePrompt.jsx";

const LINK_STYLE = { padding: "var(--space-2) var(--space-3)" };

/** Admin surfaces get the admin nav variant; everything else gets the player one. */
export function isAdminSection(pathname) {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

/**
 * The persistent top navigation bar shown on every authenticated screen except
 * the active story-play screen (022-persistent-nav-redesign-done FR-001–FR-004,
 * FR-007–FR-009).
 *
 * Per `specs/designs/README.md` the bar has two variants — Player and Admin —
 * selected by which section is being viewed, not by rendering both at once.
 * The cross-role link into the other variant ("Admin" from the player bar,
 * "Player view" from the admin bar) appears only when the account actually
 * holds both capabilities, so the bar never advertises a destination its route
 * guard would refuse (FR-008, SC-004).
 *
 * Visibility is derived entirely from capabilities `useCapabilities()` already
 * fetched from the server — this bar grants no access of its own.
 */
export function NavBar() {
  const { instance, accounts } = useMsal();
  const { pathname } = useLocation();
  const { hasPlayer, hasAdministrator } = useCapabilities();
  const published = useRefreshContext();

  const account = accounts[0];
  const userName = account?.name ?? account?.username ?? "";

  const [activeSessionId, setActiveSessionId] = useState(null);
  const [promptOpen, setPromptOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failureMessage, setFailureMessage] = useState(null);

  // Exactly one item can match, since every destination has a distinct path (FR-007).
  const current = (path) => (pathname === path ? "page" : undefined);

  // "In progress" means the server's own active-game flag on an unconcluded session
  // (research.md Decision 6) — never client state, and a failed lookup must never
  // block sign-out (FR-004).
  const handleSignOut = async (event) => {
    event.preventDefault();
    try {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      const data = await listSavedGames(tokenResponse.accessToken);
      // The list is already server-filtered to status == "active" sessions
      // (contracts/api.md) — it carries no `status` field of its own.
      const active = (data.sessions || []).find((s) => s.isActiveForPlayer);
      if (active) {
        setActiveSessionId(active.sessionId);
        setFailureMessage(null);
        setPromptOpen(true);
        return;
      }
    } catch {
      // Lookup failed — fall through to a plain sign-out rather than blocking it.
    }
    instance.logoutRedirect();
  };

  const handleSaveAndSignOut = async () => {
    setSaving(true);
    try {
      const tokenResponse = await instance.acquireTokenSilent({ ...loginRequest, account });
      await saveCheckpoint(tokenResponse.accessToken, activeSessionId);
    } catch {
      setFailureMessage("We couldn't record that checkpoint, but your progress is safe.");
    } finally {
      // Reset before redirecting (not just on the failure path) so the prompt can
      // recover if logoutRedirect() doesn't actually navigate away.
      setSaving(false);
      instance.logoutRedirect();
    }
  };

  const handleSignOutWithoutSaving = () => {
    setPromptOpen(false);
    instance.logoutRedirect();
  };

  const handleCancelSignOut = () => {
    setPromptOpen(false);
    setActiveSessionId(null);
  };

  // An admin viewing an admin surface gets the admin bar. A user with only
  // player capability always gets the player bar, even if a stray path looks
  // admin-ish — they can't be on an admin screen anyway (ProtectedRoute).
  const showAdminVariant = hasAdministrator && isAdminSection(pathname);

  return (
    <>
    <nav className="nav" style={{ gap: 0 }}>
      <span className="nav-brand" style={{ marginRight: "var(--space-5)" }}>
        Lantern
        {showAdminVariant && (
          <span
            style={{
              fontWeight: 400,
              fontSize: "13px",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--color-accent-700)",
              marginLeft: "var(--space-2)",
            }}
          >
            Admin
          </span>
        )}
      </span>

      {showAdminVariant ? (
        <>
          <Link to="/admin" style={LINK_STYLE} aria-current={current("/admin")}>
            Stories
          </Link>
          <Link
            to="/admin/stories/new"
            style={LINK_STYLE}
            aria-current={current("/admin/stories/new")}
          >
            New story
          </Link>
          <Link
            to="/admin/accounts"
            style={LINK_STYLE}
            aria-current={current("/admin/accounts")}
          >
            People
          </Link>
          {hasPlayer && (
            <>
              <span className="nav-divider" style={{ margin: "0 var(--space-4)" }} />
              <Link to="/menu" style={LINK_STYLE}>
                Player view
              </Link>
            </>
          )}
        </>
      ) : (
        hasPlayer && (
          <>
            <Link to="/menu" style={LINK_STYLE} aria-current={current("/menu")}>
              My stories
            </Link>
            {/* No badges route exists yet; matches 02-story-select.html's own
                placeholder link. Wired up by whichever feature builds badges. */}
            <a href="#" style={LINK_STYLE} onClick={(event) => event.preventDefault()}>
              Badges
            </a>
            {hasAdministrator && (
              <Link to="/admin" style={LINK_STYLE}>
                Admin
              </Link>
            )}
          </>
        )
      )}

      {/* Trailing cluster: an explicit mount point for the page-published
          refresh control (019-spa-refresh-button — RefreshContext), plus
          sign-out and identity. */}
      <span
        data-nav-slot="trailing-actions"
        style={{
          marginLeft: "auto",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-4)",
          minWidth: 0,
        }}
      >
        {published && <RefreshButton onClick={published.refresh} loading={published.loading} />}
        <a href="/login" style={LINK_STYLE} onClick={handleSignOut}>
          Sign out
        </a>
        <span className="tag tag-neutral truncate" style={{ maxWidth: "22ch" }}>
          {userName}
        </span>
      </span>
    </nav>
    {promptOpen && (
      <LogoutSavePrompt
        saving={saving}
        failureMessage={failureMessage}
        onSave={handleSaveAndSignOut}
        onDontSave={handleSignOutWithoutSaving}
        onCancel={handleCancelSignOut}
      />
    )}
    </>
  );
}

export default NavBar;
