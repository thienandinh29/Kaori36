// Shapes of the English pack's API responses (apps/api/app/api/grammar.py, vocab.py).
import type { DecisionTrace } from "@/lib/contracts";

export type Level = "A1" | "A2" | "B1" | "B2" | "C1";
export const LEVELS: readonly Level[] = ["A1", "A2", "B1", "B2", "C1"];

export interface Question {
  item_id: string;
  prompt: string;
  options: string[];
  draft: boolean; // shown with a "Bản nháp" badge
  number: number;
  total: number | null; // null for the adaptive level test
}

export interface LevelResult {
  grammar_level: Level;
  vocab_level: Level;
  ielts_vi: string; // shown exactly as the API words it
  known_milestones: string[];
  questions: number;
}

export interface Feedback {
  correct: boolean;
  key: string;
  misconception: string | null;
  misconception_vi: string | null;
}

export interface Step {
  question: Question | null;
  run_id: string | null;
  kind: string | null;
  finished: Record<string, unknown> | null;
  traces: DecisionTrace[];
  feedback: Feedback | null; // runs only: the answer just given
}

export type RunOutcome =
  | {
      kind: "milestone";
      result: "pass" | "gap" | "fail";
      opened: string[];
      learn_next: string | null;
    }
  | { kind: "checks"; learn_next: string | null }
  | { kind: "practice"; node: string; p_known: number; mastered: boolean };

export type VocabKind = "meaning" | "gapfill" | "collocation" | "wordform";

export interface VocabItem {
  id: string;
  kind: VocabKind;
  instruction_vi: string;
  prompt: string;
  options: string[] | null; // multiple choice when set, typed otherwise
  hint: string | null; // first letter, for typed answers
}

export interface WordCard {
  key: string;
  lemma: string;
  pos: string;
  level: string;
  /** British pronunciation between slashes, e.g. /tʃuːz/, or null when the list has none. */
  ipa: string | null;
  definition: string;
  vi: string | null;
  example: string;
}

export interface VocabEntry {
  item: VocabItem;
  is_new: boolean;
  card: WordCard | null;
  due_at: string | null;
}

export interface VocabSession {
  entries: VocabEntry[];
  due: number;
  new_today: number;
  new_left_today: number;
  /** New words not started yet at the chosen level(s), before the daily limit. */
  new_available: number;
}

export interface VocabLevel {
  level: Level;
  words: number;
  started: number;
  due: number;
}

export interface VocabLevels {
  levels: VocabLevel[];
  suggested: Level;
}

export interface VocabAnswer {
  correct: boolean;
  accepted: string;
  card: WordCard;
  due_at: string;
  trace: DecisionTrace;
}

export type MilestoneStatus = "mastered" | "known" | "partial" | "unknown";

export interface HiddenNode {
  slug: string;
  name_vi: string;
  p_known: number;
  known: boolean;
}

export interface Milestone {
  slug: string;
  name_vi: string;
  level: Level;
  status: MilestoneStatus;
  needs: string[];
  /** Locked: none of it known or worked on, and a milestone before it is not known yet. */
  locked: boolean;
  /** Milestones directly before this one that are not known yet. */
  waiting_for: string[];
  hidden: HiddenNode[];
}

export interface Roadmap {
  course: string;
  level_test: LevelResult | null;
  milestones: Milestone[];
  next_milestone: string | null;
  learn_next: string | null;
  learn_next_trace: DecisionTrace | null;
}

// Writing (specs/writing/step-2.1.md).
export type EssayStatus = "queued" | "analysing" | "done" | "failed";
export const LINKING_GROUPS = [
  "addition",
  "contrast",
  "cause_effect",
  "example",
  "sequence",
  "opinion",
  "conclusion",
] as const;
export type LinkingGroup = (typeof LINKING_GROUPS)[number];

/** A chart built from data (step 2.5); the page draws it, never a picture a model made. */
export interface ChartFigure {
  title: string;
  alt_vi: string;
  chart_type: "line" | "bar" | "pie" | "table";
  categories: string[];
  series: { name: string; values: number[] }[];
  unit: string;
  x_label: string;
  y_label: string;
}

export interface WritingPrompt {
  id: string;
  task: 1 | 2;
  type: string;
  level: Level;
  status: "draft" | "reviewed";
  prompt: string;
  /** Task 1 only */
  figure: ChartFigure | null;
}

/** What the code found when it checked a Task 1 essay against its chart (step 2.5). */
export interface Task1Check {
  numbers: { text: string; supported: boolean }[];
  features: {
    kind: string;
    series: string | null;
    category: string | null;
    text: string;
    covered: boolean;
  }[];
  overview: boolean;
}

export interface EssaySummary {
  id: string;
  prompt_id: string;
  status: EssayStatus;
  words: number | null;
  submitted_at: string;
}

/** An error LanguageTool found; typed by ERRANT and mapped to a node when it can be (step 2.2). */
export interface GrammarIssue {
  id: number;
  sentence: string;
  sentence_start: number;
  start: number;
  end: number;
  text: string;
  suggestion: string | null;
  category: string;
  errant_type: string | null;
  node: string | null;
  node_vi: string | null;
  explain_vi: string | null;
  /** it moved the learner's mastery of `node` */
  evidence: boolean;
  /** "llm": proposed by the model (step 2.4), shown as "gợi ý từ AI", never evidence */
  source: "languagetool" | "llm";
}

export const CRITERIA = ["tr", "cc", "lr", "gra"] as const;
export type Criterion = (typeof CRITERIA)[number];

/** A feedback point; every quote was checked to be in the essay (step 2.4). */
export interface FeedbackPoint {
  kind: "strength" | "issue";
  point_vi: string;
  quotes: string[];
}

export interface EssayFeedback {
  criteria: Record<Criterion, FeedbackPoint[]>;
  /** points removed because none of their quotes was in the essay */
  dropped: number;
}

export interface CorrectionState {
  tries: number;
  accepted: boolean;
  answer_shown: boolean;
}

/** One change in a rewrite, found by the code's own diff; the reason only when it matches. */
export interface RewriteChange {
  original: string;
  revised: string;
  why_vi: string | null;
}

export type CheckState = "passed" | "failed" | "not_run";

export interface Rewrite {
  id: string;
  paragraph: number;
  target_band: number;
  status: "queued" | "working" | "done" | "rejected" | "failed";
  result: {
    original: string;
    rewrite: string;
    changes: RewriteChange[];
    checks: Record<"length" | "languagetool" | "scorer" | "cefr", CheckState>;
  } | null;
  reason_vi: string | null;
}

export interface PhraseEntry {
  phrase_id: string;
  prompt: string;
  hint: string;
  is_new: boolean;
  /** shown only before the first question */
  phrase: string | null;
}

export interface PhraseSession {
  saved: number;
  entries: PhraseEntry[];
}

export interface PhraseAnswer {
  correct: boolean;
  accepted: string;
  due_at: string;
}

export interface CorrectionResult {
  accepted: boolean;
  tries: number;
  answer: string | null;
  feedback_vi: string;
}

export interface Complexity {
  sentences: number;
  clauses_per_sentence: number;
  complex_sentence_share: number;
}

/** The band as a range, never a point (step 2.3). */
export interface BandRange {
  band_low: number;
  band_high: number;
  /** wider than 1.5 bands: shown as "không chắc" */
  uncertain: boolean;
  status: "draft" | "validated";
  truncated: boolean;
  /** why the range is shown as "không chắc" (step 2.4's disagreement rule) */
  uncertain_reason: string | null;
}

/** What tools measured (steps 2.1 to 2.3); the band, when present, is a calibrated range. */
export interface EssayResult {
  words: number;
  sentences: number;
  paragraphs: number;
  min_words: number;
  long_enough: boolean;
  avg_sentence_words: number;
  longest_sentence_words: number;
  /** group → phrase → times used */
  linking: Partial<Record<LinkingGroup, Record<string, number>>>;
  linking_groups_used: number;
  /** step 2.2 on; null when nothing was checked (then `grammarUnavailableVi` says why), absent before */
  grammar?: { issues: GrammarIssue[] } | null;
  grammarUnavailableVi?: string | null;
  complexity?: Complexity | null;
  /** which task this essay answered; absent on essays analysed before step 2.5 */
  task?: 1 | 2;
  task1?: Task1Check;
  /** step 2.3 on; null when no band is shown (then `scoreUnavailableVi` says why) */
  score?: BandRange | null;
  scoreUnavailableVi?: string | null;
  /** step 2.4 on; null when there is none (then `feedbackUnavailableVi` says why) */
  feedback?: EssayFeedback | null;
  feedbackUnavailableVi?: string | null;
}

export interface Essay {
  id: string;
  prompt: WritingPrompt | null;
  text: string;
  status: EssayStatus;
  submitted_at: string;
  result: EssayResult | null;
  failure_vi: string | null;
  /** issue id -> the learner's self-correction (step 2.4) */
  corrections: Record<string, CorrectionState>;
  /** paragraph rewrites, oldest first (step 2.4b) */
  rewrites: Rewrite[];
}
