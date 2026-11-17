// The lesson player's logic (specs/grammar-lessons), pure and tested: what is on screen at each step.
// The player stops at actions that wait (say, ask, pause); the others apply at once, as in OpenMAIC.
import type {
  Action,
  CefrLevel,
  LessonView,
  TimePoint,
  TimeSpan,
} from "./types";

export type BoardItem =
  | { kind: "table"; rows: string[][] }
  | { kind: "timeline"; points: TimePoint[]; spans: TimeSpan[] }
  | { kind: "text"; text: string };

export interface Example {
  id: string;
  en: string;
  vi: string;
  target: string;
}

export interface Screen {
  scene: number;
  board: BoardItem[];
  examples: Example[];
  spotlight: string | null;
  subtitle: { en: string; vi: string } | null;
  ask: string | null;
  pause: boolean;
}

export interface Step {
  scene: number;
  action: Action;
}

const WAITS = new Set<Action["do"]>(["say", "ask", "pause"]);

export function steps(lesson: LessonView): Step[] {
  return lesson.scenes.flatMap((s, scene) =>
    s.actions.map((action) => ({ scene, action })),
  );
}

/** What the screen shows after applying steps 0..index (inclusive). */
export function screenAt(lesson: LessonView, index: number): Screen {
  const all = steps(lesson);
  const screen: Screen = {
    scene: 0,
    board: [],
    examples: [],
    spotlight: null,
    subtitle: null,
    ask: null,
    pause: false,
  };
  for (let i = 0; i <= Math.min(index, all.length - 1); i++) {
    const { scene, action: a } = all[i]!;
    if (scene !== screen.scene) {
      screen.scene = scene;
      screen.examples = []; // a new scene starts with new examples; the board stays
      screen.spotlight = null;
    }
    screen.ask = null;
    screen.pause = false;
    switch (a.do) {
      case "say":
        screen.subtitle = { en: a.en, vi: a.vi };
        break;
      case "show_example":
        screen.examples = [...screen.examples, a].slice(-3);
        break;
      case "spotlight":
        screen.spotlight = a.example;
        break;
      case "board_table":
        screen.board = [...screen.board, { kind: "table", rows: a.rows }];
        break;
      case "board_timeline":
        screen.board = [
          ...screen.board,
          { kind: "timeline", points: a.points, spans: a.spans },
        ];
        break;
      case "board_write":
        screen.board = [...screen.board, { kind: "text", text: a.text }];
        break;
      case "board_clear":
        screen.board = [];
        break;
      case "ask":
        screen.ask = a.checkpoint;
        screen.subtitle = null; // the checkpoint card shows the question; old words would confuse
        break;
      case "pause":
        screen.pause = true;
        break;
    }
  }
  return screen;
}

/** The first waiting step at or after `from`; the end (steps.length) when there is none. */
export function nextStop(lesson: LessonView, from: number): number {
  const all = steps(lesson);
  for (let i = Math.max(0, from); i < all.length; i++)
    if (WAITS.has(all[i]!.action.do)) return i;
  return all.length;
}

/** The waiting step before `index`, or the first one. */
export function previousStop(lesson: LessonView, index: number): number {
  const all = steps(lesson);
  for (let i = Math.min(index, all.length) - 1; i >= 0; i--)
    if (WAITS.has(all[i]!.action.do)) return i;
  return nextStop(lesson, 0);
}

/** The first stop of a scene: "Xem lại cảnh này" after a mistake (the engine chooses the scene). */
export function sceneStop(lesson: LessonView, sceneId: string): number {
  const all = steps(lesson);
  const scene = lesson.scenes.findIndex((s) => s.id === sceneId);
  const first = all.findIndex((s) => s.scene === scene);
  return scene < 0 || first < 0 ? nextStop(lesson, 0) : nextStop(lesson, first);
}

export type Status = "idle" | "playing" | "paused" | "done";

export interface PlayerState {
  status: Status;
  index: number; // the current stop
}

export type PlayerEvent =
  | { type: "start" }
  | { type: "next" }
  | { type: "previous" }
  | { type: "pause" }
  | { type: "resume" }
  | { type: "scene"; id: string };

export function initial(): PlayerState {
  return { status: "idle", index: -1 };
}

export function reduce(
  lesson: LessonView,
  state: PlayerState,
  event: PlayerEvent,
): PlayerState {
  const end = steps(lesson).length;
  const at = (index: number): PlayerState => ({
    status: index >= end ? "done" : "playing",
    index,
  });
  switch (event.type) {
    case "start":
      return at(nextStop(lesson, 0));
    case "next":
      if (state.status === "idle") return at(nextStop(lesson, 0));
      return at(nextStop(lesson, state.index + 1));
    case "previous":
      return at(previousStop(lesson, state.index));
    case "pause":
      return state.status === "playing"
        ? { ...state, status: "paused" }
        : state;
    case "resume":
      return state.status === "paused"
        ? { ...state, status: "playing" }
        : state;
    case "scene":
      return at(sceneStop(lesson, event.id));
  }
}

/** Subtitles on by default (review, 17 Nov): Vietnamese only at A1, both from A2. */
export function subtitleDefaults(level: CefrLevel): {
  en: boolean;
  vi: boolean;
} {
  return { en: level !== "A1", vi: true };
}

/** `text` split so that each target phrase (whole words, any case) can be highlighted. */
export function marks(
  text: string,
  targets: string[],
): { text: string; mark: boolean }[] {
  const wanted = targets.filter((t) => t.trim()).map(escape);
  if (!wanted.length) return [{ text, mark: false }];
  const re = new RegExp(
    `(?<![A-Za-z'])(${wanted.join("|")})(?![A-Za-z'])`,
    "gi",
  );
  const out: { text: string; mark: boolean }[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    if (m.index > last)
      out.push({ text: text.slice(last, m.index), mark: false });
    out.push({ text: m[0], mark: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last), mark: false });
  return out;
}

function escape(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** x position (0..1) of a time on the board's timeline (-4 past .. 0 now .. 4 future). */
export function timeX(at: number): number {
  return (Math.max(-4, Math.min(4, at)) + 4) / 8;
}
