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

describe("Admin sign-in flow", () => {
  it("renders both game and admin menu items for a dual-capability user", () => {
    mockUseCapabilities.mockReturnValue({
      hasPlayer: true,
      hasAdministrator: true,
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
    expect(screen.getByText(/^administration$/i)).toBeInTheDocument();
  });
});
