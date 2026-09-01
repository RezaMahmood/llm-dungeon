import { renderHook, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const acquireTokenSilent = vi.fn().mockResolvedValue({ accessToken: "test-token" });
const loginRedirect = vi.fn();
// Stable references across renders — mirrors real MSAL context behavior, and
// avoids retriggering the hook's memoized callback (and its effect) on every render.
const mockInstance = { acquireTokenSilent, loginRedirect };
const mockAccounts = [{ username: "user@example.com" }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const getMe = vi.fn();
vi.mock("../../src/services/authService.js", () => ({
  getMe: (...args) => getMe(...args),
}));

import { CapabilitiesProvider, useCapabilities } from "../../src/hooks/useCapabilities.js";

// The fetching logic lives in `CapabilitiesProvider` (a single shared instance
// mounted once at the app root); `useCapabilities()` is just its context
// consumer, so the hook under test must be rendered inside the provider.
const wrapper = ({ children }) => (
  <MemoryRouter>
    <CapabilitiesProvider>{children}</CapabilitiesProvider>
  </MemoryRouter>
);

describe("useCapabilities", () => {
  afterEach(() => {
    getMe.mockReset();
    loginRedirect.mockReset();
    mockNavigate.mockReset();
    sessionStorage.clear();
  });

  it("returns hasPlayer true, hasAdministrator false for a Player-only user", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(true);
    expect(result.current.hasAdministrator).toBe(false);
  });

  it("returns both true for a dual-role user", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });

    const { result } = renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(true);
    expect(result.current.hasAdministrator).toBe(true);
  });

  it("returns both false for a user with no capabilities", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: false, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(false);
    expect(result.current.hasAdministrator).toBe(false);
  });

  it("navigates to /login with a session-expired reason on a 401 from /api/auth/me (FR-008)", async () => {
    getMe.mockRejectedValueOnce({ response: { status: 401 } });

    renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/login", {
        state: { reason: "session-expired" },
      }),
    );
    expect(loginRedirect).not.toHaveBeenCalled();
  });

  it("navigates to /login with a session-expired reason when MSAL fails to silently renew the token (FR-008)", async () => {
    // acquireTokenSilent can fail purely client-side (expired refresh token,
    // consent/MFA step-up required) without ever reaching the backend — found
    // via the user's own T024 walkthrough: a hard reload showed "Access not
    // granted" with zero /api/auth/me requests in the network panel.
    acquireTokenSilent.mockRejectedValueOnce(new Error("InteractionRequiredAuthError"));

    renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/login", {
        state: { reason: "session-expired" },
      }),
    );
    expect(getMe).not.toHaveBeenCalled();

    acquireTokenSilent.mockResolvedValue({ accessToken: "test-token" });
  });

  it("does not loop into a second navigation if /api/auth/me 401s again in the same session", async () => {
    // Simulates the redirect loop found live: sign-in completes, MSAL comes
    // back with a fresh token, but /api/auth/me still 401s (a structural
    // token problem, not a stale session) — repeatedly navigating here risked
    // the same kind of thrash the old loginRedirect loop caused.
    sessionStorage.setItem("llmdungeon.capabilities.redirectAttempted", "1");
    getMe.mockRejectedValueOnce({ response: { status: 401 } });

    const { result } = renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(result.current.error).toBeTruthy();
    expect(result.current.denied).toBe(false);
  });

  it("clears the redirect guard after a successful fetch", async () => {
    sessionStorage.setItem("llmdungeon.capabilities.redirectAttempted", "1");
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(sessionStorage.getItem("llmdungeon.capabilities.redirectAttempted")).toBeNull();
  });
});
