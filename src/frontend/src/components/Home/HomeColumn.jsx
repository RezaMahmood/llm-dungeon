/**
 * Shared column shell behind `ReadyToPlayList.jsx` and `InProgressList.jsx`
 * (specs/designs/07-home-spec.md §5) — factored out after `/code-review high` flagged the
 * two as near-identical copies of the same kicker/heading/loading/error scaffold, differing
 * only in their inner content.
 */
export function HomeColumn({
  as: Tag = "section",
  className,
  kicker,
  heading,
  loading,
  loadingMessage = "Loading…",
  error,
  errorMessage = "Couldn't load. Please try again.",
  children,
}) {
  return (
    <Tag className={className}>
      <div className="home-colhead">
        <div className="home-kicker">{kicker}</div>
        <h2>{heading}</h2>
      </div>
      <div className="home-colbody">
        {loading ? (
          <p className="text-muted">{loadingMessage}</p>
        ) : error ? (
          <p role="alert" className="text-muted">
            {errorMessage}
          </p>
        ) : (
          children
        )}
      </div>
    </Tag>
  );
}

export default HomeColumn;
