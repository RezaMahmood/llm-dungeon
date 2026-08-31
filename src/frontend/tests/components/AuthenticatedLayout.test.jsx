import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({
    instance: { logoutRedirect: vi.fn() },
    accounts: [{ name: "Ada B.", username: "ada@example.test" }],
  }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import AuthenticatedLayout from "../../src/components/Layout/AuthenticatedLayout.jsx";

const renderAt = (path) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AuthenticatedLayout>
        <p>screen content</p>
      </AuthenticatedLayout>
    </MemoryRouter>,
  );

describe("AuthenticatedLayout header selection (FR-001, FR-006, SC-002)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: true,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });
  });

  it.each(["/menu", "/admin", "/admin/accounts", "/admin/stories/new"])(
    "renders the nav bar (not the title bar) on %s",
    (path) => {
      renderAt(path);

      expect(screen.getByRole("navigation")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /pause & exit/i })).not.toBeInTheDocument();
    },
  );

  it("renders the title bar (not the nav bar) on the story-play screen", () => {
    renderAt("/game");

    expect(screen.getByRole("button", { name: /pause & exit/i })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("always renders its children below whichever header it chose", () => {
    for (const path of ["/menu", "/game"]) {
      const { unmount } = renderAt(path);
      expect(screen.getByText("screen content")).toBeInTheDocument();
      unmount();
    }
  });
});
