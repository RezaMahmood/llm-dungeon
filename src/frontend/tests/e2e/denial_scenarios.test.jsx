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

describe("Denial scenarios", () => {
  it("valid token, not on allow-list: shows denied message, no menu", () => {
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
    expect(screen.queryByText(/start or continue game/i)).not.toBeInTheDocument();
  });

  it("valid token, on allow-list, no capabilities: shows provisioning message", () => {
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

    expect(screen.getByText(/access pending/i)).toBeInTheDocument();
  });

  it("Player capability: admin menu item is not rendered", () => {
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

    expect(screen.queryByText(/^administration$/i)).not.toBeInTheDocument();
  });
});
