import { useState } from "react";

// One pass, not a conversation (#227): the idea goes to the model once and the suggestion
// it returns lands in the world prompt field below. Nothing is echoed back here — there is
// no exchange history to show, so the panel stays a single input and a button.
export function IdeaPanel({ onSuggestWorldPrompt }) {
  const [idea, setIdea] = useState("");
  const [status, setStatus] = useState("idle"); // idle | suggesting | error

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!idea.trim()) return;

    setStatus("suggesting");
    try {
      await onSuggestWorldPrompt(idea);
      setIdea("");
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="field">
      <label htmlFor="story-idea">Describe your story idea</label>
      <p className="text-muted" style={{ margin: "4px 0 8px", fontSize: "13px" }}>
        Sent to the story engine once — it writes the world prompt below, which you can then edit.
      </p>
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "10px" }}>
        <input
          id="story-idea"
          className="input"
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
          placeholder="Describe your idea"
        />
        <button type="submit" className="btn btn-primary" disabled={status === "suggesting"}>
          {status === "suggesting" ? "Writing…" : "Suggest world prompt"}
        </button>
      </form>
      {status === "error" && (
        <div role="alert" className="text-muted">
          Could not write a world prompt from that idea. Please try again.
        </div>
      )}
    </div>
  );
}

export default IdeaPanel;
