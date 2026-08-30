import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import CompletionCriteriaFields from "../../../src/components/Admin/StoryWizard/CompletionCriteriaFields.jsx";

describe("CompletionCriteriaFields", () => {
  it("commits a single success condition without showing the any/all selector", async () => {
    const onChange = vi.fn();
    render(<CompletionCriteriaFields completionCriteria={null} onChange={onChange} />);

    await userEvent.click(screen.getByRole("button", { name: /add success condition/i }));
    await userEvent.type(screen.getByLabelText(/success condition/i), "Find the keeper");
    await userEvent.tab();

    expect(onChange).toHaveBeenCalledWith({
      maxDurationMinutes: null,
      successConditions: ["Find the keeper"],
      failureConditions: [],
      rule: null,
    });
    expect(screen.queryByText(/how should multiple conditions combine/i)).not.toBeInTheDocument();
  });

  it("shows the any/all rule selector once more than one condition is defined", () => {
    render(
      <CompletionCriteriaFields
        completionCriteria={{
          maxDurationMinutes: 20,
          successConditions: ["Find the keeper"],
          failureConditions: ["Leave the cove"],
          rule: "any",
        }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/how should multiple conditions combine/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^any$/i)).toBeChecked();
  });

  it("clears the whole structure when the last success condition is removed", async () => {
    const onChange = vi.fn();
    render(
      <CompletionCriteriaFields
        completionCriteria={{ maxDurationMinutes: null, successConditions: ["Find the keeper"], failureConditions: [], rule: null }}
        onChange={onChange}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /remove/i }));

    expect(onChange).toHaveBeenCalledWith(null);
  });
});
