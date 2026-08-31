import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();
const logoutRedirect = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: { logoutRedirect },
    accounts: [{ name: "Ada B.", username: "ada@example.test" }],
  }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import { RefreshProvider, usePublishRefresh } from "../../src/context/RefreshContext.jsx";
import NavBar from "../../src/components/Layout/NavBar.jsx";

const capabilities = (hasPlayer, hasAdministrator) => ({
  hasPlayer,
  hasAdministrator,
  loading: false,
  error: null,
  denied: false,
  refetch: vi.fn(),
});

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <NavBar />
    </MemoryRouter>,
  );

const linkNames = () => screen.getAllByRole("link").map((el) => el.textContent.trim());

describe("NavBar capability-driven visibility (FR-002, FR-003, FR-008, SC-004)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the admin link set on an admin surface for an admin-only account", () => {
    mockUseCapabilities.mockReturnValue(capabilities(false, true));
    renderAt("/admin");

    expect(screen.getByRole("link", { name: "Stories" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New story" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "People" })).toBeInTheDocument();
    // No player capability -> no cross-link into an experience they cannot open.
    expect(screen.queryByRole("link", { name: "Player view" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "My stories" })).not.toBeInTheDocument();
  });

  it("shows the player link set and no admin links for a player-only account", () => {
    mockUseCapabilities.mockReturnValue(capabilities(true, false));
    renderAt("/menu");

    expect(screen.getByRole("link", { name: "My stories" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Badges" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Admin" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Stories" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "New story" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "People" })).not.toBeInTheDocument();
  });

  it("offers the cross-role link into the other experience for a dual-capability account", () => {
    mockUseCapabilities.mockReturnValue(capabilities(true, true));

    // On an admin surface: admin bar, with a way over to the player side.
    const { unmount } = renderAt("/admin/accounts");
    expect(screen.getByRole("link", { name: "Player view" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "People" })).toBeInTheDocument();
    unmount();

    // On a player surface: player bar, with a way back into admin.
    renderAt("/menu");
    expect(screen.getByRole("link", { name: "Admin" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My stories" })).toBeInTheDocument();
  });

  it("shows no primary destinations when the account has neither capability", () => {
    mockUseCapabilities.mockReturnValue(capabilities(false, false));
    renderAt("/menu");

    expect(linkNames()).toEqual(["Sign out"]);
  });

  it("always shows sign out and the user's name regardless of capability (FR-004)", () => {
    for (const [player, admin] of [
      [false, false],
      [true, false],
      [false, true],
      [true, true],
    ]) {
      mockUseCapabilities.mockReturnValue(capabilities(player, admin));
      const { unmount } = renderAt("/menu");

      expect(screen.getByRole("link", { name: "Sign out" })).toBeInTheDocument();
      expect(screen.getByText("Ada B.")).toBeInTheDocument();
      unmount();
    }
  });

  it("keeps a trailing-actions slot so a later Refresh control needs no restructuring", () => {
    mockUseCapabilities.mockReturnValue(capabilities(true, true));
    const { container } = renderAt("/menu");

    const slot = container.querySelector('[data-nav-slot="trailing-actions"]');
    expect(slot).not.toBeNull();
    expect(within(slot).getByRole("link", { name: "Sign out" })).toBeInTheDocument();
    // This feature deliberately ships no Refresh control (019's scope).
    expect(screen.queryByRole("button", { name: /refresh/i })).not.toBeInTheDocument();
  });
});

describe("NavBar RefreshContext consumption (019-spa-refresh-button, contracts/refresh-control.md)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCapabilities.mockReturnValue(capabilities(true, false));
  });

  function Publisher({ refresh, loading }) {
    usePublishRefresh({ refresh, loading });
    return null;
  }

  const renderWithProvider = (path, { refresh, loading } = {}) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <RefreshProvider>
          {refresh && <Publisher refresh={refresh} loading={loading} />}
          <NavBar />
        </RefreshProvider>
      </MemoryRouter>,
    );

  it("renders RefreshButton in trailing-actions only when RefreshContext has a published value", () => {
    const { container } = renderWithProvider("/menu");

    expect(screen.queryByRole("button", { name: /refresh/i })).not.toBeInTheDocument();

    const slot = container.querySelector('[data-nav-slot="trailing-actions"]');
    expect(slot).not.toBeNull();
  });

  it("renders the published RefreshButton and wires it to the publisher's refresh/loading", async () => {
    const refresh = vi.fn();
    const { container, rerender } = renderWithProvider("/menu", { refresh, loading: false });

    const slot = container.querySelector('[data-nav-slot="trailing-actions"]');
    const button = within(slot).getByRole("button", { name: /refresh/i });
    expect(button).not.toBeDisabled();

    await userEvent.click(button);
    expect(refresh).toHaveBeenCalledTimes(1);

    rerender(
      <MemoryRouter initialEntries={["/menu"]}>
        <RefreshProvider>
          <Publisher refresh={refresh} loading />
          <NavBar />
        </RefreshProvider>
      </MemoryRouter>,
    );
    // aria-label stays the static "Refresh"; the "Refreshing…" swap is in the
    // visible text content, not the accessible name.
    const refreshedButton = screen.getByRole("button", { name: /^refresh$/i });
    expect(refreshedButton).toBeDisabled();
    expect(refreshedButton).toHaveTextContent("Refreshing…");
  });
});

describe("NavBar current-section indication (FR-007, US4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ["/menu", "My stories", true, false],
    ["/admin", "Stories", false, true],
    ["/admin/stories/new", "New story", false, true],
    ["/admin/accounts", "People", false, true],
  ])("marks exactly one item current on %s", (path, expectedLabel, player, admin) => {
    mockUseCapabilities.mockReturnValue(capabilities(player, admin));
    renderAt(path);

    const currentItems = screen
      .getAllByRole("link")
      .filter((el) => el.getAttribute("aria-current") === "page");

    expect(currentItems).toHaveLength(1);
    expect(currentItems[0]).toHaveTextContent(expectedLabel);
  });
});
