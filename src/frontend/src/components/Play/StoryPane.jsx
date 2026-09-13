import { memo, useEffect, useRef } from "react";

import "./Play.css";

// Chapter numbers are spelled out in the kicker line ("Chapter three — …", per
// specs/designs/03-play.html) rather than shown as a numeral there — the numeral itself
// is the large .ovnum above it. Stories are short-form (constitution Principle XII,
// "Right-Sized Scope"), so twenty covers every realistic chapter count; beyond that,
// falling back to the digits is a graceful degradation, not a broken chapter identifier.
const CHAPTER_WORDS = [
  null,
  "one",
  "two",
  "three",
  "four",
  "five",
  "six",
  "seven",
  "eight",
  "nine",
  "ten",
  "eleven",
  "twelve",
  "thirteen",
  "fourteen",
  "fifteen",
  "sixteen",
  "seventeen",
  "eighteen",
  "nineteen",
  "twenty",
];

function chapterWord(number) {
  return CHAPTER_WORDS[number] ?? String(number);
}

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
  const latest = turns[turns.length - 1];
  const progress = latest?.progress;

  // Scroll to the newest content on mount and after every new turn (029, FR-004) —
  // the transcript is the only part of the play surface that ever moves.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (scroller) scroller.scrollTop = scroller.scrollHeight;
  }, [turns.length]);

  return (
    <div ref={scrollerRef} className="storyscroll play-transcript" aria-live="polite">
      <div style={{ maxWidth: "64ch" /* no token covers this measure — deliberate exception */ }}>
        {/* Chapter identifier (spec.md FR-002, research.md Decision 1): the numeral is
            progress.current, the title is the same (latest) turn's locationLabel — no
            server-authored chapter title exists or is needed. Shown only when the story
            reports progress; scrolls away with the rest of the transcript, not fixed. */}
        {progress && (
          <>
            <div className="ovnum play-chapter-num" style={{ color: "var(--color-accent-200)" }}>
              {String(progress.current).padStart(2, "0")}
            </div>
            <div className="play-chapter-line">
              Chapter {chapterWord(progress.current)} — {latest.locationLabel}
            </div>
          </>
        )}
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
