import { Link } from "react-router-dom";

/**
 * Placeholder admin landing page. Full authoring UI lands in
 * 005-story-publishing / 012-story-editing-and-review.
 */
export function AdminPage() {
  return (
    <div style={{ padding: "var(--space-6)" }}>
      <h1>Administration</h1>
      <p>Administration features loading…</p>
      <Link to="/admin/accounts" className="btn btn-secondary">
        Accounts
      </Link>
    </div>
  );
}

export default AdminPage;
