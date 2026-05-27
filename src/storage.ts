import type { ProgressState } from "./types";

const STORAGE_KEY = "patent-zeglarza-progress-v1";

export const emptyProgress = (): ProgressState => ({
  version: 1,
  records: {},
  exam: null,
});

export const loadProgress = (): ProgressState => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyProgress();
    const parsed = JSON.parse(raw) as ProgressState;
    if (
      parsed.version !== 1 ||
      !parsed.records ||
      typeof parsed.records !== "object" ||
      (parsed.exam !== null && typeof parsed.exam !== "object")
    ) {
      return emptyProgress();
    }
    return { ...emptyProgress(), ...parsed };
  } catch {
    return emptyProgress();
  }
};

export const saveProgress = (progress: ProgressState): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch {
    // Browsers can block storage. The app still works for the current session.
  }
};

export const clearProgress = (): void => {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignored for the same reason as saveProgress.
  }
};

export const storageKey = STORAGE_KEY;
