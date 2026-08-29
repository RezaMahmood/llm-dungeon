import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AdminMenuItem from "../../src/components/Menu/AdminMenuItem.jsx";

describe("AdminMenuItem", () => {
  it("renders when included in the tree", () => {
    render(<AdminMenuItem onClick={() => {}} />);
    expect(screen.getByRole("button", { name: /administration/i })).toBeInTheDocument();
  });

  it("calls onClick when clicked, simulating navigation to admin endpoint", async () => {
    const onClick = vi.fn();
    render(<AdminMenuItem onClick={onClick} />);

    await userEvent.click(screen.getByRole("button", { name: /administration/i }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
