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
        manualChunks: {
          msal: ["@azure/msal-browser", "@azure/msal-react"],
          react: ["react", "react-dom", "react-router-dom"],
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
