export function GameMenuItem({ label = "Start or Continue Game", onClick }) {
  return (
    <button type="button" className="btn btn-block rowhov menu-item" onClick={onClick}>
      {label}
    </button>
  );
}

export default GameMenuItem;
