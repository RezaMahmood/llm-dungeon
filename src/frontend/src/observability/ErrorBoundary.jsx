import { Component } from "react";

import { appInsights } from "./appInsights.js";

/**
 * Reports a caught render error to Application Insights (FR-004, contract §3)
 * before showing the same fallback UI as `components/Common/ErrorBoundary.jsx` —
 * this replaces that boundary at the app root so render errors are both shown to
 * the user and captured as telemetry.
 */
export class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    appInsights.trackException({
      exception: error,
      properties: { componentStack: info?.componentStack },
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" style={{ padding: "var(--space-6)" }}>
          Something went wrong. Please refresh the page.
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
