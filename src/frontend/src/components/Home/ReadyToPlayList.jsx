import HomeColumn from "./HomeColumn.jsx";
import StoryRow from "./StoryRow.jsx";

/** Left column — "Ready to play" (specs/designs/07-home-spec.md §5.1, FR-002). Loading
 * and error states match `GameSetup/AdventureList.jsx`'s existing pattern. */
export function ReadyToPlayList({ stories, loading, error, onPlay }) {
  return (
    <HomeColumn
      className="home-col home-col-main"
      kicker="Start something new"
      heading="Ready to play"
      loading={loading}
      loadingMessage="Loading stories…"
      error={error}
      errorMessage="Couldn't load stories. Please try again."
    >
      {stories.length === 0 ? (
        // Not the "no stories published" case the design spec puts out of scope —
        // this is every published story already having a session in progress.
        <p className="text-muted">You&rsquo;ve started every story that&rsquo;s available right now.</p>
      ) : (
        stories.map((story) => <StoryRow key={story.id} story={story} onPlay={onPlay} />)
      )}
    </HomeColumn>
  );
}

export default ReadyToPlayList;
