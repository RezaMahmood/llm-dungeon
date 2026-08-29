import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";

import AuthProvider from "./components/Auth/AuthProvider.jsx";
import ProtectedRoute from "./components/Auth/ProtectedRoute.jsx";
import ErrorBoundary from "./components/Common/ErrorBoundary.jsx";
import LoginScreen from "./components/Login/LoginScreen.jsx";
import MainMenu from "./components/Menu/MainMenu.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import GamePage from "./pages/GamePage.jsx";

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
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
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
