import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const mockUseCapabilities = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { logoutRedirect: vi.fn() } }),
}));

vi.mock("../../src/hooks/useCapabilities.js", () => ({
  useCapabilities: () => mockUseCapabilities(),
}));

import MainMenu from "../../src/components/Menu/MainMenu.jsx";

describe("MainMenu", () => {
  it("renders the game menu item when user has Player capability", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <MainMenu />
      </MemoryRouter>,
    );

    expect(screen.getByText(/start or continue game/i)).toBeInTheDocument();
    expect(screen.queryByText(/administration/i)).not.toBeInTheDocument();
  });

  it("does not render the admin menu item for a Player-only user", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <MainMenu />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("button", { name: /^administration$/i })).not.toBeInTheDocument();
  });

  it("displays an error message if the API returns denied", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: true,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <MainMenu />
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/access not granted/i);
  });

  it("shows the no-access message when the user has no capabilities", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: false,
      hasAdministrator: false,
      loading: false,
      error: null,
      denied: false,
      refetch: vi.fn(),
    });

    render(
      <MemoryRouter>
        <MainMenu />
      </MemoryRouter>,
    );

    expect(screen.getByText(/access provisioned/i)).toBeInTheDocument();
  });
});
