import StoryRow from "./StoryRow.jsx";

/** Left column — "Ready to play" (specs/designs/07-home-spec.md §5.1, FR-002). Loading
 * and error states match `GameSetup/AdventureList.jsx`'s existing pattern. */
export function ReadyToPlayList({ stories, loading, error, onPlay }) {
  return (
    <section className="home-col home-col-main">
      <div className="home-colhead">
        <div className="home-kicker">Start something new</div>
        <h2>Ready to play</h2>
      </div>
      <div className="home-colbody">
        {loading ? (
          <p className="text-muted">Loading stories…</p>
        ) : error ? (
          <p role="alert" className="text-muted">
            Couldn&rsquo;t load stories. Please try again.
          </p>
        ) : (
          stories.map((story) => <StoryRow key={story.id} story={story} onPlay={onPlay} />)
        )}
      </div>
    </section>
  );
}

export default ReadyToPlayList;
