import "./Home.css";

/** One "Ready to play" row (specs/designs/07-home-spec.md §5.1, FR-002). The whole row
 * is a single link; the Play button is a `<span>` inside it so the row reads as one
 * target (07-home-spec.md §8). */
export function StoryRow({ story, onPlay }) {
  const kicker = [story.tone, story.sessionLengthMinutes ? `${story.sessionLengthMinutes} min` : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <a
      className="home-listrow home-rowhov"
      href="#play"
      onClick={(event) => {
        event.preventDefault();
        onPlay(story);
      }}
    >
      <div>
        <div className="card-kicker">{kicker}</div>
        <div style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: "22px", lineHeight: 1.15, marginTop: "6px" }}>
          {story.name}
        </div>
        {story.blurb && (
          <p style={{ margin: "6px 0 0", fontSize: "15px", maxWidth: "60ch" }}>{story.blurb}</p>
        )}
        <div className="card-meta" style={{ marginTop: "8px" }}>
          Reading level: {story.readingLevel}
        </div>
      </div>
      <span className="btn btn-secondary" style={{ padding: "11px 16px" }}>
        Play
      </span>
    </a>
  );
}

export default StoryRow;
