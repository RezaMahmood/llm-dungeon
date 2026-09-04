import { useNavigate } from "react-router-dom";

import { usePublishRefresh } from "../../context/RefreshContext.jsx";
import { useCapabilities } from "../../hooks/useCapabilities.js";
import AccessDeniedScreen from "../Login/AccessDeniedScreen.jsx";
import AdminMenuItem from "./AdminMenuItem.jsx";
import GameMenuItem from "./GameMenuItem.jsx";
import "./MainMenu.css";

export function MainMenu() {
  const navigate = useNavigate();
  const { hasPlayer, hasAdministrator, loading, error, denied, refetch } = useCapabilities();
  // useCapabilities already re-fetches fresh from /api/auth/me on every call
  // (FR-011) and exposes its own loading/error state, so this screen
  // publishes it directly rather than wrapping it in a second useRefreshable
  // fetch cycle — NavBar renders the shared RefreshButton from this (FR-001/FR-002).
  usePublishRefresh({ refresh: refetch, loading });

  if (loading) {
    return <div className="main-menu">Loading…</div>;
  }

  if (denied) {
    return <AccessDeniedScreen />;
  }

  if (error) {
    return (
      <div className="main-menu">
        <p role="alert">Something went wrong. Please try again.</p>
        <button type="button" className="btn btn-secondary" onClick={refetch}>
          Try again
        </button>
      </div>
    );
  }

  const hasNoCapabilities = !hasPlayer && !hasAdministrator;

  return (
    <div className="main-menu">
      {/* The signed-in identity, sign-out and wayfinding now live in the shared
          nav bar (AuthenticatedLayout), so this screen owns only its content. */}
      <h1>My stories</h1>
      <hr className="hr" />
      {hasNoCapabilities && (
        <div className="no-access-message">
          <h2>Access Pending</h2>
          <p>
            Your account is registered but no roles have been assigned yet. Contact your
            administrator to grant access.
          </p>
        </div>
      )}
      {!hasNoCapabilities && (
        <div className="menu-list">
          {hasPlayer && <GameMenuItem onClick={() => navigate("/game")} />}
          {hasAdministrator && <AdminMenuItem onClick={() => navigate("/admin")} />}
        </div>
      )}
    </div>
  );
}

export default MainMenu;
