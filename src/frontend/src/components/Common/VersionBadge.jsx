import { useCallback, useRef, useState } from "react";

import { UNKNOWN_VERSION, getBackendVersion, getFrontendVersion } from "../../services/versionService.js";

const TOOLTIP_ID = "version-badge-tooltip";

/**
 * Small "?" affordance fixed to the bottom-left of every page (issue #255).
 * Hovering — or focusing it with the keyboard — reveals the deployed frontend
 * and backend versions.
 *
 * Mounted once at the app root rather than per page, and deliberately outside
 * the router and auth providers: it needs neither, and so renders on the login
 * screen exactly as it does on an authenticated page.
 */
export function VersionBadge() {
  const [open, setOpen] = useState(false);
  const [versions, setVersions] = useState(null);
  // A ref, not state: this must gate the fetch synchronously within one render
  // pass, so a hover that immediately re-enters can't start a second request.
  const requested = useRef(false);

  const load = useCallback(() => {
    if (requested.current) return;
    requested.current = true;
    // allSettled, not all: the two components deploy independently, so a
    // backend that is down or mid-deploy must still leave the frontend version
    // readable, and vice versa.
    Promise.allSettled([getFrontendVersion(), getBackendVersion()]).then(([frontend, backend]) => {
      setVersions({
        frontend: frontend.status === "fulfilled" ? frontend.value : UNKNOWN_VERSION,
        backend: backend.status === "fulfilled" ? backend.value : UNKNOWN_VERSION,
      });
    });
  }, []);

  const show = useCallback(() => {
    load();
    setOpen(true);
  }, [load]);

  const hide = useCallback(() => setOpen(false), []);

  return (
    <div
      style={{ position: "fixed", left: "var(--space-3)", bottom: "var(--space-3)", zIndex: 20 }}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      {open && (
        <div
          role="tooltip"
          id={TOOLTIP_ID}
          style={{
            position: "absolute",
            bottom: "calc(100% + var(--space-2))",
            left: 0,
            padding: "var(--space-2) var(--space-3)",
            background: "var(--color-surface)",
            border: "1px solid var(--color-divider)",
            boxShadow: "var(--shadow-md)",
            fontSize: 12,
            lineHeight: 1.55,
            whiteSpace: "nowrap",
          }}
        >
          <div
            className="text-muted"
            style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase" }}
          >
            Deployed version
          </div>
          <VersionRow label="Frontend" version={versions?.frontend} />
          <VersionRow label="Backend" version={versions?.backend} />
        </div>
      )}
      <button
        type="button"
        className="btn btn-secondary"
        aria-label="Version information"
        aria-expanded={open}
        aria-describedby={open ? TOOLTIP_ID : undefined}
        onFocus={show}
        onBlur={hide}
        // Touch devices never fire hover, so tapping has to work as a toggle.
        onClick={() => (open ? hide() : show())}
        style={{
          width: 22,
          height: 22,
          padding: 0,
          fontSize: 12,
          lineHeight: 1,
          background: "var(--color-surface)",
          // Unobtrusive at rest, fully legible once the reader has engaged with it.
          opacity: open ? 1 : 0.7,
        }}
      >
        ?
      </button>
    </div>
  );
}

function VersionRow({ label, version }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-4)" }}>
      <span className="text-muted">{label}</span>
      {/* Nothing yet means the request is still in flight — the versions land together. */}
      <span style={{ fontVariantNumeric: "tabular-nums" }}>{version ?? "…"}</span>
    </div>
  );
}

export default VersionBadge;
