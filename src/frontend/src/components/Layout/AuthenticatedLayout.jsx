import { useLocation } from "react-router-dom";

import { RefreshProvider } from "../../context/RefreshContext.jsx";
import NavBar from "./NavBar.jsx";
import TitleBar from "./TitleBar.jsx";

/** The one route that gets the compact title bar instead of the full nav bar. */
export const STORY_PLAY_PATH = "/game";

/**
 * Wraps every authenticated screen with the shared header: the persistent nav
 * bar everywhere, except the active story-play screen, which gets the compact
 * title bar so it keeps the full reading height (FR-001, FR-006).
 *
 * Exactly one of the two always renders — never both, never neither (SC-002).
 * This is a purely presentational wrapper; it is mounted from inside
 * `ProtectedRoute`, so unauthenticated users never reach it (FR-009).
 */
export function AuthenticatedLayout({ children }) {
  const { pathname } = useLocation();
  const isStoryPlay = pathname === STORY_PLAY_PATH;

  return (
    <RefreshProvider>
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", minWidth: 0 }}>
        {isStoryPlay ? <TitleBar /> : <NavBar />}
        <div style={{ flex: 1, minHeight: 0, minWidth: 0 }}>{children}</div>
      </div>
    </RefreshProvider>
  );
}

export default AuthenticatedLayout;
