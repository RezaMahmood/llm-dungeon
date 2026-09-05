/**
 * Application Insights JS SDK bootstrap (FR-004/FR-005 — the frontend leg of this
 * feature's telemetry). Microsoft ships no supported OTel→Application Insights
 * browser exporter (research.md §3), so this SDK stands in for a literal OTel Web
 * SDK on the browser leg only; it defaults to W3C Trace-Context propagation, the
 * same standard the backend's OTel HTTP instrumentation reads, so frontend and
 * backend spans still merge into one correlated Application Insights trace.
 */
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { ApplicationInsights, DistributedTracingModes } from "@microsoft/applicationinsights-web";
import { ReactPlugin } from "@microsoft/applicationinsights-react-js";

export const reactPlugin = new ReactPlugin();

const connectionString = import.meta.env.VITE_APPLICATIONINSIGHTS_CONNECTION_STRING;

export const appInsights = new ApplicationInsights({
  config: {
    connectionString: connectionString || undefined,
    extensions: [reactPlugin],
    distributedTracingMode: DistributedTracingModes.W3C,
    enableCorsCorrelation: true,
    // Deliberately NOT enabling enableRequestHeaderTracking/
    // enableResponseHeaderTracking: the AjaxPlugin captures header *values*
    // verbatim when these are on, with no default redaction — since every
    // outbound call carries an X-Custom-Authorization bearer token, turning
    // these on would export it straight into Application Insights, violating
    // FR-006/contract §3 ("never request/response body or header values").
    autoTrackPageVisitTime: true,
  },
});

let initialized = false;

/**
 * Initializes the SDK once at app startup. A no-op when
 * VITE_APPLICATIONINSIGHTS_CONNECTION_STRING isn't set (e.g. local dev without
 * it configured) — mirrors the backend's `setup_observability()` guard.
 * Resilience when Application Insights itself is unreachable or misconfigured
 * is 018-observability-resilience's scope, not this one.
 */
export function initializeAppInsights() {
  if (initialized || !connectionString) {
    return appInsights;
  }
  appInsights.loadAppInsights();
  // Explicit, rather than relying only on the SDK's own default global-error
  // instrumentation, so an unhandled JS error/rejection outside the React tree
  // is reliably reported with a message and stack trace (FR-004, contract §3)
  // regardless of browser/environment differences in how that auto-instrumentation
  // attaches. Guarded by a flag on `window` itself, not just this module's
  // `initialized` — `window` outlives a single module instance (e.g. Vite HMR
  // re-evaluating this file), so a module-scoped guard alone would let a second
  // pair of listeners attach and double-report every subsequent error.
  if (!window.__appInsightsGlobalErrorHandlersInstalled) {
    window.addEventListener("error", (event) => {
      appInsights.trackException({ exception: event.error ?? new Error(event.message) });
    });
    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      appInsights.trackException({ exception: reason });
    });
    window.__appInsightsGlobalErrorHandlersInstalled = true;
  }
  initialized = true;
  return appInsights;
}

/**
 * Reports a PageView event on every route change (FR-004, contract §3). React
 * Router v7 doesn't expose a `history` object compatible with the SDK's
 * automatic route-view plugin option, so this drives it explicitly instead —
 * render once inside <Router>, alongside the routed content.
 */
export function PageViewTracker() {
  const location = useLocation();

  useEffect(() => {
    // Deliberately excludes location.search: query strings can carry sensitive
    // data (e.g. OAuth codes/state) and are high-cardinality, the same reason
    // the backend strips query strings from http.route (FR-006).
    appInsights.trackPageView({ name: location.pathname, uri: location.pathname });
  }, [location.pathname]);

  return null;
}
