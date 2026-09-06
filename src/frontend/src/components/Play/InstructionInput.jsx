import { useState } from "react";

/**
 * Free-text action input — always available alongside SuggestedActions (Constitution
 * "Readability & interaction requirements" #4-5). `disabled` covers the concluded/
 * locked-out states (FR-010, FR-013).
 */
export function InstructionInput({ onSubmit, disabled, value, onChange }) {
  const [internalValue, setInternalValue] = useState("");
  const isControlled = value !== undefined;
  const currentValue = isControlled ? value : internalValue;
  const setValue = isControlled ? onChange : setInternalValue;

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = currentValue.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    if (!isControlled) setInternalValue("");
  };

  return (
    <form style={{ display: "flex", gap: "10px", alignItems: "stretch" }} onSubmit={handleSubmit}>
      <label htmlFor="play-instruction-input" style={{ position: "absolute", width: "1px", height: "1px", overflow: "hidden" }}>
        What do you do next?
      </label>
      <input
        id="play-instruction-input"
        className="input"
        placeholder="What do you do next?"
        style={{ flex: 1, minHeight: "52px", fontSize: "18px", padding: "10px 14px" }}
        value={currentValue}
        onChange={(event) => setValue(event.target.value)}
        disabled={disabled}
      />
      <button className="btn btn-primary" type="submit" style={{ padding: "0 26px", fontSize: "16px" }} disabled={disabled}>
        Go
      </button>
    </form>
  );
}

export default InstructionInput;
