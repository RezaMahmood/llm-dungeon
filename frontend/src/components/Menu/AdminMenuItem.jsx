export function AdminMenuItem({ label = "Administration", onClick }) {
  return (
    <button type="button" className="btn btn-block rowhov menu-item" onClick={onClick}>
      {label}
    </button>
  );
}

export default AdminMenuItem;
