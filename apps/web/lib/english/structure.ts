import { vi } from "@/messages/vi";
import type { Development, EssayStructure, StructureFinding } from "./types";

const w = vi.english.writing;

/** What a structure finding says, in Vietnamese (specs/writing/step-2.11.md, 2.11b). */
export function findingText(f: StructureFinding, s: EssayStructure): string {
  const part = f.part === null ? "" : (s.parts[f.part - 1]?.text ?? "");
  return w.findings[f.kind]
    .replace("{part}", part)
    .replace("{n}", String(f.paragraph ?? ""));
}

/** How a body paragraph develops its point; `null` means the code could not check it. */
export function developmentText(d: Development | null): string {
  return d === null ? w.development.unknown : w.development[d];
}

/** Which parts of the question a body paragraph answers, as "trả lời phần 1, 2". */
export function answersText(answers: number[]): string {
  return answers.length === 0
    ? w.structureAnswersNone
    : w.structureAnswers.replace("{parts}", answers.join(", "));
}

/** Whether a part was answered: yes, no, or the code cannot tell. */
export function answeredText(answered: boolean | null): string {
  if (answered === null) return w.structureUnsure;
  return answered ? w.structureAnswered : w.structureMissing;
}
