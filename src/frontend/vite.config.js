import { resolve } from "path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { visualizer } from "rollup-plugin-visualizer";

// Opt-in bundle-composition report (`npm run build:analyze`) rather than generated on every
// build — makes future manualChunks decisions evidence-based instead of guesswork, without
// adding a plugin pass to the build every contributor runs.
const plugins = [react()];
if (process.env.ANALYZE) {
  plugins.push(visualizer({ filename: "dist/stats.html", gzipSize: true, brotliSize: true }));
}

export default defineConfig({
  plugins,
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      // MSAL v5's redirect bridge (see msalConfig.js) needs its own HTML entry
      // so it's emitted as a standalone page rather than bundled into index.html.
      input: {
        main: resolve(import.meta.dirname, "index.html"),
        redirect: resolve(import.meta.dirname, "redirect.html"),
      },
      output: {
        // Vendor libraries change far less often than app code — splitting them
        // into their own chunks means a routine app deploy doesn't invalidate the
        // browser's cache of these (msal-browser in particular is the largest).
        manualChunks(id) {
          if (id.includes("@azure/msal-browser") || id.includes("@azure/msal-react")) {
            return "msal";
          }
          if (
            id.includes("@microsoft/applicationinsights-web") ||
            id.includes("@microsoft/applicationinsights-react-js")
          ) {
            return "appInsights";
          }
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom/") ||
            id.includes("node_modules/react-router-dom/") ||
            id.includes("node_modules/react-router/")
          ) {
            return "react";
          }
          if (id.includes("node_modules/axios/")) {
            return "axios";
          }
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.js",
    globals: true,
  },
});
