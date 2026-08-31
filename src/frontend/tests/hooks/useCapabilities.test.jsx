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

import { useCapabilities } from "../../src/hooks/useCapabilities.js";

const wrapper = ({ children }) => <MemoryRouter>{children}</MemoryRouter>;

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
