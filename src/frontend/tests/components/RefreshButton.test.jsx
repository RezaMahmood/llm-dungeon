import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RefreshButton from "../../src/components/Common/RefreshButton.jsx";

describe("RefreshButton (contracts/refresh-control.md)", () => {
  it("renders the agreed .btn.btn-ghost markup with the Refresh label", () => {
    render(<RefreshButton onClick={vi.fn()} loading={false} />);

    const button = screen.getByRole("button", { name: /refresh/i });
    expect(button).toHaveClass("btn", "btn-ghost");
    expect(button).not.toBeDisabled();
    expect(button).toHaveTextContent("Refresh");
  });

  it("is disabled and shows Refreshing… while loading", () => {
    render(<RefreshButton onClick={vi.fn()} loading />);

    const button = screen.getByRole("button", { name: /refreshing/i });
    expect(button).toBeDisabled();
  });

  it("calls onClick when activated", async () => {
    const onClick = vi.fn();
    render(<RefreshButton onClick={onClick} loading={false} />);

    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
