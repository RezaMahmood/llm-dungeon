import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { lazy, Suspense } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import AuthProvider from "./components/Auth/AuthProvider.jsx";
import ProtectedRoute from "./components/Auth/ProtectedRoute.jsx";
import ErrorBoundary from "./components/Common/ErrorBoundary.jsx";
import LoginScreen from "./components/Login/LoginScreen.jsx";
import MainMenu from "./components/Menu/MainMenu.jsx";
import { CapabilitiesProvider } from "./context/CapabilitiesContext.jsx";

// Lazy-loaded: each page becomes its own chunk, fetched on navigation instead of
// bundled into the initial (login/menu) payload — keeps the always-loaded bundle
// small since most visits never reach the admin or game pages in the same session.
const AdminAccountsPage = lazy(() => import("./pages/AdminAccountsPage.jsx"));
const AdminPage = lazy(() => import("./pages/AdminPage.jsx"));
const AdminStoryWizardPage = lazy(() => import("./pages/AdminStoryWizardPage.jsx"));
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
                      <MainMenu />
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
                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </Suspense>
          </CapabilitiesProvider>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
