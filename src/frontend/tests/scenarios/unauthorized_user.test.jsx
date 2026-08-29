import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const loginPopup = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { loginPopup } }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

import LoginScreen from "../../src/components/Login/LoginScreen.jsx";

describe("Unauthorized user scenario", () => {
  it("does not render any menu items on the login screen", () => {
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/start or continue game/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/administration/i)).not.toBeInTheDocument();
  });

  it("shows a generic failure message rather than an account-specific one when sign-in errors", async () => {
    loginPopup.mockRejectedValueOnce({ errorCode: "network_error" });
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: /sign in with microsoft/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/check your connection/i);
  });
});
