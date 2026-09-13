import { memo, useEffect, useRef } from "react";

import "./Play.css";

/**
 * Scrolling narrative history for the play surface (specs/designs/03-play.html,
 * 008-core-gameplay-done). Renders every turn so far: the narrative text, and — when
 * present — the player's own input for that turn, oldest first.
 *
 * Memoized: PlayPage re-renders on every keystroke in InstructionInput (its own
 * `inputValue` state), but `turns` only gets a new array reference when a turn is
 * actually added — without this, every keystroke would re-map the whole turn history.
 */
export const StoryPane = memo(function StoryPane({ turns }) {
  const scrollerRef = useRef(null);

  // Scroll to the newest content on mount and after every new turn (029, FR-004) —
  // the transcript is the only part of the play surface that ever moves.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (scroller) scroller.scrollTop = scroller.scrollHeight;
  }, [turns.length]);

  return (
    <div ref={scrollerRef} className="storyscroll play-transcript" aria-live="polite">
      <div style={{ maxWidth: "64ch" /* no token covers this measure — deliberate exception */ }}>
        {turns.map((turn) => (
          <div key={turn.turnNumber}>
            {turn.playerInput != null && (
              <div className="play-entry">
                <div className="play-label">You</div>
                <p className="play-text play-text-player">{turn.playerInput}</p>
              </div>
            )}
            <div className="play-entry">
              <div className="play-label">The story</div>
              <p className="play-text">{turn.narrativeText}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

export default StoryPane;
