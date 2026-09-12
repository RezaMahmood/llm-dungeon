import "./Home.css";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** Derives a contextual "{Day} {time of day}" kicker from the viewer's own clock
 * (FR-020), e.g. "Wednesday afternoon". */
export function greetingKicker(date = new Date()) {
  const day = DAY_NAMES[date.getDay()];
  const hour = date.getHours();
  const timeOfDay = hour < 5 ? "night" : hour < 12 ? "morning" : hour < 17 ? "afternoon" : hour < 21 ? "evening" : "night";
  return `${day} ${timeOfDay}`;
}

function ledeCopy(inProgressCount) {
  if (inProgressCount === 0) {
    return "Nothing on the go right now. Pick a story to start and it will save itself as you play.";
  }
  if (inProgressCount === 1) {
    return "You have one story on the go. Everything is saved where you left it.";
  }
  return `You have ${inProgressCount} stories on the go. Everything is saved where you left it.`;
}

/** Fixed-height welcome band (specs/designs/07-home-spec.md §4, FR-005, FR-020). */
export function WelcomeBand({ firstName, inProgressCount }) {
  return (
    <div className="home-hero">
      <div className="home-kicker">{greetingKicker().toUpperCase()}</div>
      <h1>Welcome back, {firstName}.</h1>
      <p className="text-muted" style={{ margin: "6px 0 0", maxWidth: "64ch", fontSize: "14px" }}>
        {ledeCopy(inProgressCount)}
      </p>
    </div>
  );
}

export default WelcomeBand;
