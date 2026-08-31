import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        // Vendor libraries change far less often than app code — splitting them
        // into their own chunks means a routine app deploy doesn't invalidate the
        // browser's cache of these (msal-browser in particular is the largest).
        manualChunks(id) {
          if (id.includes("@azure/msal-browser") || id.includes("@azure/msal-react")) {
            return "msal";
          }
          if (
            id.includes("node_modules/react/") ||
            id.includes("node_modules/react-dom/") ||
            id.includes("node_modules/react-router-dom/") ||
            id.includes("node_modules/react-router/")
          ) {
            return "react";
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
