import { useLocation } from "react-router-dom";

import { PlayTitleProvider } from "../../context/PlayTitleContext.jsx";
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

  // Every other screen keeps `minHeight: 100vh` (a floor, so content taller than the
  // viewport still grows the page and scrolls normally — index.css's own comment on why
  // it carries no blanket `overflow: hidden`). Story play needs the opposite: a *fixed*
  // `100vh` ceiling, not just a floor, or nothing downstream constrains height at all —
  // `.play-shell`'s `height: 100%; overflow: hidden` (Play.css) has no definite ancestor
  // height to resolve against, so the transcript's growth pushes the whole page taller
  // and `body` scrolls instead of just the transcript pane (FR-001).
  const shellStyle = isStoryPlay
    ? { display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", minWidth: 0 }
    : { display: "flex", flexDirection: "column", minHeight: "100vh", minWidth: 0 };

  return (
    <RefreshProvider>
      <PlayTitleProvider>
        <div style={shellStyle}>
          {isStoryPlay ? <TitleBar /> : <NavBar />}
          <div style={{ flex: 1, minHeight: 0, minWidth: 0 }}>{children}</div>
        </div>
      </PlayTitleProvider>
    </RefreshProvider>
  );
}

export default AuthenticatedLayout;
