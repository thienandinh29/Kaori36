import type { KeyValueStore } from "./learner";

/** This tab's storage: an own question or an exam in progress survives a reload, not the tab. */
export function sessionStore(): KeyValueStore | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}
