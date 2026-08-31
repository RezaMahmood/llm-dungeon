/**
 * Placeholder game landing page. Full gameplay UI lands in 008-core-gameplay.
 *
 * The header for this screen is the compact TitleBar supplied by
 * AuthenticatedLayout (FR-006) — this page renders only the story area below it.
 */
export function GamePage() {
  return (
    <div style={{ maxWidth: "1020px", padding: "var(--space-6) var(--space-4) 64px" }}>
      <p className="text-muted">Game features loading…</p>
    </div>
  );
}

export default GamePage;
