import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const loginPopup = vi.fn();
const mockNavigate = vi.fn();

vi.mock("@azure/msal-react", () => ({
  useMsal: () => ({ instance: { loginPopup } }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import LoginScreen from "../../src/components/Login/LoginScreen.jsx";

describe("LoginScreen", () => {
  beforeEach(() => {
    loginPopup.mockReset();
    mockNavigate.mockReset();
  });

  it("renders the Sign in with Microsoft button", () => {
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /sign in with microsoft/i })).toBeInTheDocument();
  });

  it("triggers the MSAL sign-in flow and navigates to /menu on success", async () => {
    loginPopup.mockResolvedValueOnce({});
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: /sign in with microsoft/i }));

    expect(loginPopup).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/menu");
  });

  it("shows a friendly error message on sign-in cancellation", async () => {
    loginPopup.mockRejectedValueOnce({ errorCode: "user_cancelled" });
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: /sign in with microsoft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/cancelled/i);
  });

  it("shows no persistent nav bar on the unauthenticated screen (FR-009)", () => {
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /sign out/i })).not.toBeInTheDocument();
    for (const label of ["Stories", "New story", "People", "My stories"]) {
      expect(screen.queryByRole("link", { name: label })).not.toBeInTheDocument();
    }
  });

  it("renders the sessionExpired message when routed here with that reason (FR-008)", () => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { reason: "session-expired" } }]}>
        <Routes>
          <Route path="/login" element={<LoginScreen />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/your session ended/i);
  });

  it("shows no sessionExpired message for a plain, never-signed-in visit", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <LoginScreen />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("styles its controls from the shared design system, not ad hoc rules", () => {
    render(
      <MemoryRouter>
        <LoginScreen />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /sign in with microsoft/i })).toHaveClass(
      "btn",
      "btn-primary",
    );
  });
});
