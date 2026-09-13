import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PendingIndicator from "../../src/components/Common/PendingIndicator.jsx";

// The non-button half of the pending-action pattern (issue #347) — used wherever an async
// backend call has no single control to grey out (screen loads, an in-flight turn).
describe("PendingIndicator (issue #347)", () => {
  it("announces itself as a status and shows a spinner beside its message", () => {
    const { container } = render(<PendingIndicator>Loading sessions…</PendingIndicator>);

    expect(screen.getByRole("status")).toHaveTextContent("Loading sessions…");
    expect(container.querySelector(".spinner")).toBeInTheDocument();
  });

  it("falls back to a generic message", () => {
    render(<PendingIndicator />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
  });
});
