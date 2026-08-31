import { useEffect } from "react";

/**
 * Arms the browser's native `beforeunload` confirmation while `isDirty` is
 * true, and removes it once the caller reports the input has been saved
 * (data-model.md's Unsaved-Changes Flag; FR-010).
 */
export function useUnsavedChangesWarning(isDirty) {
  useEffect(() => {
    if (!isDirty) return undefined;

    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
      return "";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);
}

export default useUnsavedChangesWarning;
