import { renderHook, waitFor } from "@testing-library/react";
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

const getMe = vi.fn();
vi.mock("../../src/services/authService.js", () => ({
  getMe: (...args) => getMe(...args),
}));

import { useCapabilities } from "../../src/hooks/useCapabilities.js";

describe("useCapabilities", () => {
  afterEach(() => {
    getMe.mockReset();
    loginRedirect.mockReset();
    sessionStorage.clear();
  });

  it("returns hasPlayer true, hasAdministrator false for a Player-only user", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(true);
    expect(result.current.hasAdministrator).toBe(false);
  });

  it("returns both true for a dual-role user", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: true } });

    const { result } = renderHook(() => useCapabilities());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(true);
    expect(result.current.hasAdministrator).toBe(true);
  });

  it("returns both false for a user with no capabilities", async () => {
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: false, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasPlayer).toBe(false);
    expect(result.current.hasAdministrator).toBe(false);
  });

  it("redirects to sign-in on a 401 from /api/auth/me", async () => {
    getMe.mockRejectedValueOnce({ response: { status: 401 } });

    renderHook(() => useCapabilities());

    await waitFor(() => expect(loginRedirect).toHaveBeenCalledTimes(1));
  });

  it("does not loop into a second redirect if /api/auth/me 401s again in the same session", async () => {
    // Simulates the redirect loop found live: sign-in completes, MSAL comes
    // back with a fresh token, but /api/auth/me still 401s (a structural
    // token problem, not a stale session) — repeatedly calling loginRedirect
    // here is what tripped Entra ID's own throttling/lockout on the account.
    sessionStorage.setItem("llmdungeon.capabilities.redirectAttempted", "1");
    getMe.mockRejectedValueOnce({ response: { status: 401 } });

    const { result } = renderHook(() => useCapabilities());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(loginRedirect).not.toHaveBeenCalled();
    expect(result.current.error).toBeTruthy();
    expect(result.current.denied).toBe(false);
  });

  it("clears the redirect guard after a successful fetch", async () => {
    sessionStorage.setItem("llmdungeon.capabilities.redirectAttempted", "1");
    getMe.mockResolvedValueOnce({ capabilities: { hasPlayer: true, hasAdministrator: false } });

    const { result } = renderHook(() => useCapabilities());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(sessionStorage.getItem("llmdungeon.capabilities.redirectAttempted")).toBeNull();
  });
});
