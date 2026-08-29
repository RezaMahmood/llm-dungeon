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
});
