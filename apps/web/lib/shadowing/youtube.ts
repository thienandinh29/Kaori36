// A pasted YouTube link to a video id (step 4.4d). Only the id is kept: the official embedded
// player plays the video, so nothing is downloaded (YouTube's terms forbid that).
const ID = /^[A-Za-z0-9_-]{11}$/;
const HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtu.be",
  "www.youtube-nocookie.com",
]);

export function videoId(link: string): string | null {
  const text = link.trim();
  if (ID.test(text)) return text;
  let url: URL;
  try {
    url = new URL(text.startsWith("http") ? text : `https://${text}`);
  } catch {
    return null;
  }
  if (!["http:", "https:"].includes(url.protocol) || !HOSTS.has(url.hostname))
    return null;
  const parts = url.pathname.split("/").filter(Boolean);
  const id =
    url.hostname === "youtu.be"
      ? parts[0]
      : parts[0] === "watch"
        ? url.searchParams.get("v")
        : ["shorts", "embed", "live", "v"].includes(parts[0] ?? "")
          ? parts[1]
          : null;
  return id && ID.test(id) ? id : null;
}

/** A loop's start and end in seconds, ordered and at least half a second apart. */
export function loopSpan(
  a: number | null,
  b: number | null,
): { from: number; to: number } | null {
  if (a === null || b === null) return null;
  const from = Math.max(0, Math.min(a, b));
  const to = Math.max(a, b);
  return to - from >= 0.5 ? { from, to } : null;
}

/** m:ss for a time in seconds. */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
