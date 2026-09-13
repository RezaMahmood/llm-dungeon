/**
 * The product's pending-action primitive (issue #347): a control that has been actioned
 * but whose request has not come back yet greys itself out, stops responding, and shows
 * a spinner beside a label saying what is happening — so a slow backend call never reads
 * as "nothing happened".
 *
 * Applied first to the destructive actions (story delete, saved-session delete, admin
 * session delete), which is where a silent no-op is most alarming and a second click is
 * most costly. It is deliberately generic so the rest of the app's async calls can adopt
 * the same language incrementally rather than each inventing its own.
 *
 * `as="span"` exists for `Home/SessionDeleteAction.jsx`, whose trigger sits inside the
 * session card's whole-card `<a>` and therefore cannot be a nested `<button>`. That
 * variant marks itself `aria-disabled` rather than `disabled` — the design system already
 * gives the two the same greyed-out look, and a natively disabled element would drop out
 * of the tab order mid-interaction (designTokens.css, Interaction states).
 */
export function Spinner() {
  // Decorative: the pending label beside it carries the meaning, and `aria-busy` on the
  // control is what actually tells a screen reader the action is in flight.
  return <span className="spinner" aria-hidden="true" />;
}

export function PendingButton({
  as = "button",
  pending = false,
  pendingLabel,
  disabled = false,
  className = "btn btn-secondary",
  onClick,
  children,
  ...rest
}) {
  const inactive = pending || disabled;

  // A blocked span still has to swallow the event: it sits inside a link, so letting the
  // click through would navigate instead of doing nothing.
  const handleClick = (event) => {
    if (inactive) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    onClick?.(event);
  };

  const content = (
    <>
      {pending && <Spinner />}
      {pending && pendingLabel ? pendingLabel : children}
    </>
  );

  if (as === "span") {
    return (
      <span {...rest} className={className} aria-busy={pending || undefined} aria-disabled={inactive || undefined} onClick={handleClick}>
        {content}
      </span>
    );
  }

  return (
    <button {...rest} type="button" className={className} aria-busy={pending || undefined} disabled={inactive} onClick={handleClick}>
      {content}
    </button>
  );
}

export default PendingButton;
