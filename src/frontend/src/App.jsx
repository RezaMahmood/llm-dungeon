import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { lazy, Suspense } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import AuthProvider from "./components/Auth/AuthProvider.jsx";
import ProtectedRoute from "./components/Auth/ProtectedRoute.jsx";
import VersionBadge from "./components/Common/VersionBadge.jsx";
import LoginScreen from "./components/Login/LoginScreen.jsx";
import { CapabilitiesProvider } from "./context/CapabilitiesContext.jsx";
import HomePage from "./pages/HomePage.jsx";
import ErrorBoundary from "./observability/ErrorBoundary.jsx";
import { PageViewTracker } from "./observability/appInsights.js";

// Lazy-loaded: each page becomes its own chunk, fetched on navigation instead of
// bundled into the initial (login/menu) payload — keeps the always-loaded bundle
// small since most visits never reach the admin or game pages in the same session.
const AdminAccountsPage = lazy(() => import("./pages/AdminAccountsPage.jsx"));
const AdminPage = lazy(() => import("./pages/AdminPage.jsx"));
const AdminStoryWizardPage = lazy(() => import("./pages/AdminStoryWizardPage.jsx"));
const AdminStoryConfigurationPage = lazy(() => import("./pages/AdminStoryConfigurationPage.jsx"));
const AdminStoryTestPlayPage = lazy(() => import("./pages/AdminStoryTestPlayPage.jsx"));
const AdminSessionsPage = lazy(() => import("./pages/AdminSessionsPage.jsx"));
const GamePage = lazy(() => import("./pages/GamePage.jsx"));

function PageFallback() {
  return (
    <div style={{ padding: "var(--space-6)" }}>
      <p className="text-muted">Loading…</p>
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <CapabilitiesProvider>
            <PageViewTracker />
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route
                  path="/login"
                  element={
                    <>
                      <UnauthenticatedTemplate>
                        <LoginScreen />
                      </UnauthenticatedTemplate>
                      <AuthenticatedTemplate>
                        <Navigate to="/menu" replace />
                      </AuthenticatedTemplate>
                    </>
                  }
                />
                <Route
                  path="/menu"
                  element={
                    <ProtectedRoute>
                      <HomePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/game"
                  element={
                    <ProtectedRoute capability="Player">
                      <GamePage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/accounts"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminAccountsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/stories/new"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminStoryWizardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/stories/:storyId"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminStoryConfigurationPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/stories/:storyId/edit"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminStoryWizardPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/stories/:storyId/test-play"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminStoryTestPlayPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/admin/sessions"
                  element={
                    <ProtectedRoute capability="Administrator">
                      <AdminSessionsPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </Suspense>
          </CapabilitiesProvider>
        </Router>
      </AuthProvider>
      {/* Outside the router and AuthProvider: it needs neither, so it renders
          on the login screen the same way it does on every other page (#255). */}
      <VersionBadge />
    </ErrorBoundary>
  );
}

export default App;
