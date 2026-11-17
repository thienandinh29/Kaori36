// The lesson as the API sends it (specs/grammar-lessons): scenes of typed actions; never an answer key.
export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1";

export interface TimePoint {
  label: string;
  at: number;
}
export interface TimeSpan {
  label: string;
  start: number;
  end: number;
  open: boolean;
}

export type Action =
  | { do: "say"; en: string; vi: string }
  | { do: "show_example"; id: string; en: string; vi: string; target: string }
  | { do: "spotlight"; example: string }
  | { do: "board_table"; rows: string[][] }
  | { do: "board_timeline"; points: TimePoint[]; spans: TimeSpan[] }
  | { do: "board_write"; text: string }
  | { do: "board_clear" }
  | { do: "ask"; checkpoint: string }
  | { do: "pause" };

export interface Scene {
  id: string;
  kind: string;
  misconceptions: string[];
  actions: Action[];
}

export interface CheckpointView {
  id: string;
  en: string;
  vi: string;
  options: string[];
}

export interface LessonView {
  node: string;
  course: string;
  level: CefrLevel;
  status: "sample" | "draft" | "reviewed";
  title_en: string;
  title_vi: string;
  noncommercial: boolean;
  sources: { candidate: string; chapter: string; licence: string }[];
  scenes: Scene[];
  checkpoints: CheckpointView[];
}

export interface LessonSummary {
  node: string;
  level: CefrLevel;
  status: LessonView["status"];
  title_en: string;
  title_vi: string;
}

export interface CheckpointResult {
  correct: boolean;
  key: string;
  explain_vi: string;
  misconception_vi: string | null;
}
