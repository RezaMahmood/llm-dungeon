import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SuggestedActions from "../../src/components/Play/SuggestedActions.jsx";

describe("SuggestedActions (008-core-gameplay)", () => {
  it("renders each suggested action and submits on click", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<SuggestedActions actions={["climb the stairs", "pick up the candle"]} onSelect={onSelect} disabled={false} />);

    await user.click(screen.getByRole("button", { name: "climb the stairs" }));

    expect(onSelect).toHaveBeenCalledWith("climb the stairs");
  });

  it("renders nothing when there are no suggested actions", () => {
    const { container } = render(<SuggestedActions actions={[]} onSelect={vi.fn()} disabled={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("disables each action button when disabled", () => {
    render(<SuggestedActions actions={["wait"]} onSelect={vi.fn()} disabled />);
    expect(screen.getByRole("button", { name: "wait" })).toBeDisabled();
  });
});
