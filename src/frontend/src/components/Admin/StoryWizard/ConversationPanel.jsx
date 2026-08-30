import { useState } from "react";

export function ConversationPanel({ exchanges = [], onSendMessage }) {
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | error

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!message.trim()) return;

    setStatus("sending");
    try {
      await onSendMessage(message);
      setMessage("");
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="field">
      <label htmlFor="story-idea-message">Tell the system about your story</label>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
        {exchanges.map((exchange, index) => (
          <p key={index} style={{ margin: 0 }}>
            <strong>{exchange.role === "administrator" ? "You" : "System"}:</strong> {exchange.message}
          </p>
        ))}
      </div>
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "10px" }}>
        <input
          id="story-idea-message"
          className="input"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Describe your idea, or answer the guiding question"
        />
        <button type="submit" className="btn btn-primary" disabled={status === "sending"}>
          {status === "sending" ? "Sending…" : "Send"}
        </button>
      </form>
      {status === "error" && (
        <div role="alert" className="text-muted">
          Could not send that message. Please try again.
        </div>
      )}
    </div>
  );
}

export default ConversationPanel;
