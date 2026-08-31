import { useMsal } from "@azure/msal-react";
import { useNavigate } from "react-router-dom";

import { useCapabilities } from "../../hooks/useCapabilities.js";
import AccessDeniedScreen from "../Login/AccessDeniedScreen.jsx";
import AdminMenuItem from "./AdminMenuItem.jsx";
import GameMenuItem from "./GameMenuItem.jsx";
import "./MainMenu.css";

export function MainMenu() {
  const navigate = useNavigate();
  const { hasPlayer, hasAdministrator, loading, error, denied, refetch } = useCapabilities();

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
          <h2>Access Provisioned</h2>
          <p>
            Your account is registered but no roles have been assigned yet. Contact your
            administrator to grant access.
          </p>
          <button type="button" className="btn btn-secondary" onClick={refetch}>
            Refresh
          </button>
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
