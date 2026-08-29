import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AccountList from "../../src/components/Admin/AccountList.jsx";

describe("AccountList", () => {
  it("lists every account with its email and roles", () => {
    render(
      <AccountList
        accounts={[
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: false },
        ]}
      />,
    );

    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    expect(screen.getByText("player@example.com")).toBeInTheDocument();
    expect(screen.getByText("Administrator")).toBeInTheDocument();
    expect(screen.getByText("Player")).toBeInTheDocument();
  });

  it("shows both roles for a merged dual-role account without duplicating rows", () => {
    render(
      <AccountList
        accounts={[{ email: "dual@example.com", roles: ["Player", "Administrator"], bound: true }]}
      />,
    );

    const rows = screen.getAllByRole("row");
    // header row + exactly one data row
    expect(rows).toHaveLength(2);
    expect(screen.getByText("Player")).toBeInTheDocument();
    expect(screen.getByText("Administrator")).toBeInTheDocument();
  });

  it("shows bound status as Signed in / Not yet signed in", () => {
    render(
      <AccountList
        accounts={[
          { email: "admin@example.com", roles: ["Administrator"], bound: true },
          { email: "player@example.com", roles: ["Player"], bound: false },
        ]}
      />,
    );

    expect(screen.getByText("Signed in")).toBeInTheDocument();
    expect(screen.getByText("Not yet signed in")).toBeInTheDocument();
  });

  it("renders an empty table when there are no accounts", () => {
    render(<AccountList accounts={[]} />);

    expect(screen.getAllByRole("row")).toHaveLength(1);
  });
});
