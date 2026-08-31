import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();
const mockInstance = { logoutRedirect: vi.fn() };
const mockAccounts = [{ homeAccountId: "home-1", username: "ada@example.test", name: "Ada B." }];

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: mockInstance, accounts: mockAccounts }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";

const capabilities = (hasPlayer, hasAdministrator) => ({
  hasPlayer,
  hasAdministrator,
  loading: false,
  error: null,
  denied: false,
  refetch: vi.fn(),
});

/** Renders the shared layout over a few real routes so nav links actually navigate. */
const renderApp = (initialPath) =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthenticatedLayout>
        <Routes>
          <Route path="/menu" element={<p>player home</p>} />
          <Route path="/admin" element={<p>admin home</p>} />
          <Route path="/admin/accounts" element={<p>people</p>} />
          <Route path="/admin/stories/new" element={<p>wizard</p>} />
        </Routes>
      </AuthenticatedLayout>
    </MemoryRouter>,
  );

const visibleLinks = () =>
  screen.getAllByRole("link").map((el) => el.textContent.trim());

describe("Nav items match granted capabilities (FR-008, SC-004)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a player-only account no admin destinations", () => {
    mockUseCapabilities.mockReturnValue(capabilities(true, false));
    renderApp("/menu");

    expect(visibleLinks()).toEqual(["My stories", "Badges", "Sign out"]);
  });

  it("shows an admin-only account no player-only destinations", () => {
    mockUseCapabilities.mockReturnValue(capabilities(false, true));
    renderApp("/admin");

    expect(visibleLinks()).toEqual(["Stories", "New story", "People", "Sign out"]);
  });

  it("shows an account with neither capability no destinations at all", () => {
    mockUseCapabilities.mockReturnValue(capabilities(false, false));
    renderApp("/menu");

    expect(visibleLinks()).toEqual(["Sign out"]);
  });
});

describe("Dual-capability accounts can move between experiences (US3 scenario 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCapabilities.mockReturnValue(capabilities(true, true));
  });

  it("crosses from the admin bar to the player experience and back", async () => {
    const user = userEvent.setup();
    renderApp("/admin");

    // Admin surface -> player view.
    await user.click(screen.getByRole("link", { name: "Player view" }));
    expect(screen.getByText("player home")).toBeInTheDocument();

    // The player bar offers the way back into admin.
    await user.click(screen.getByRole("link", { name: "Admin" }));
    expect(screen.getByText("admin home")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Player view" })).toBeInTheDocument();
  });
});

describe("Reaching any section from the wizard in one click (US1, SC-001)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCapabilities.mockReturnValue(capabilities(false, true));
  });

  it.each([
    ["People", "people"],
    ["Stories", "admin home"],
  ])("reaches %s from the wizard without a back button", async (linkName, expectedText) => {
    const user = userEvent.setup();
    renderApp("/admin/stories/new");

    await user.click(screen.getByRole("link", { name: linkName }));

    expect(screen.getByText(expectedText)).toBeInTheDocument();
    // The same bar is still present on the destination (US1 scenario 3).
    expect(screen.getByRole("link", { name: "New story" })).toBeInTheDocument();
  });
});
