// The English pack's calls, through the same-origin proxy (/api/backend): the API key stays on the server.
import {
  parseQueue,
  type RejectReason,
  type ReviewQueue,
  type ReviewStatus,
  parsePassageReview,
  parseReviewTexts,
  type PassageReview,
  type ReviewTexts,
} from "@/lib/reading/review";
import { DataError } from "@/lib/decode";
import { parseToday, type Today } from "@/lib/english/today";
import { parseMaps, type Maps } from "@/lib/english/maps";
import {
  parseAnswer,
  parseText,
  parseTexts,
  type Answer,
  type AnswerResult,
  type ReadingText,
  type TextSummary,
} from "@/lib/reading/practice";
import {
  parseStartedTest,
  parseTestResult,
  type StartedTest,
  type TestResult,
  type submission,
} from "@/lib/reading/test";
import {
  parseRecheck,
  parseRecheckResult,
  type RecheckQuestion,
  type RecheckResult,
} from "@/lib/english/recheck";
import {
  parsePhraseAnswer,
  parsePhraseSession,
  parseCorrection,
  parseEssay,
  parseEssaySummaries,
  parseLevelResult,
  parseRoadmap,
  parseStep,
  parseVocabAnswer,
  parseVocabCheck,
  parseVocabLevels,
  parseVocabSession,
  parseWritingPrompts,
} from "./decode";
import type {
  CorrectionResult,
  PhraseAnswer,
  PhraseSession,
  Essay,
  EssaySummary,
  Level,
  LevelResult,
  Roadmap,
  Step,
  VocabAnswer,
  VocabCheck,
  VocabLevels,
  VocabSession,
  WritingPrompt,
} from "./types";
import { CONSENT } from "./writing";
import {
  parseCheckpointResult,
  parseLesson,
  parseLessonSummaries,
} from "@/lib/lesson/decode";
import {
  parsePrompts,
  parseRecording,
  parseRecordingResult,
  parseRecordings,
  type Label,
  type RecordingDetail,
  type PronunciationPrompts,
  type RecordingResult,
  type RecordingRow,
} from "@/lib/pronunciation/types";
import type {
  CheckpointResult,
  LessonSummary,
  LessonView,
} from "@/lib/lesson/types";

export const VOCAB_LIST = "core-seed";

export const COURSE = "english-ielts";

type Fetch = typeof fetch;

export function englishClient(fetcher: Fetch = (...a) => fetch(...a)) {
  async function request(
    path: string,
    init: RequestInit = {},
  ): Promise<unknown> {
    let response: Response;
    try {
      response = await fetcher(`/api/backend/${path}`, {
        ...init,
        cache: "no-store",
        signal: init.signal ?? AbortSignal.timeout(25000),
      });
    } catch {
      throw new DataError("network");
    }
    if (!response.ok)
      throw new DataError(
        response.status === 503 ? "configuration" : "failed",
        response.status,
      );
    if (response.status === 204) return null;
    try {
      return await response.json();
    } catch {
      throw new DataError("contract");
    }
  }
  const post = (path: string, body: unknown) =>
    request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  return {
    async createLearner(displayName: string): Promise<string> {
      const d = (await post("learners", { display_name: displayName })) as {
        learner_id?: unknown;
      };
      if (typeof d?.learner_id !== "string") throw new DataError("contract");
      return d.learner_id;
    },
    async startLevelTest(
      learnerId: string,
      target: Level | null,
    ): Promise<Step> {
      return parseStep(
        await post("level-tests", {
          learner_id: learnerId,
          course: COURSE,
          target,
        }),
      );
    },
    async answerLevelTest(
      learnerId: string,
      testId: string,
      itemId: string,
      answer: string,
    ): Promise<Step> {
      return parseStep(
        await post(`level-tests/${testId}/answers`, {
          learner_id: learnerId,
          item_id: itemId,
          answer,
        }),
      );
    },
    async startMilestoneTest(
      learnerId: string,
      milestone: string,
    ): Promise<Step> {
      return parseStep(
        await post(`milestones/${milestone}/tests`, {
          learner_id: learnerId,
          course: COURSE,
        }),
      );
    },
    // Lessons before practice (specs/grammar-lessons).
    async lessons(learnerId: string): Promise<LessonSummary[]> {
      const q = new URLSearchParams({ learner_id: learnerId, course: COURSE });
      return parseLessonSummaries(await request(`lessons?${q}`));
    },
    async lesson(learnerId: string, node: string): Promise<LessonView> {
      const q = new URLSearchParams({ learner_id: learnerId, course: COURSE });
      return parseLesson(await request(`lessons/${node}?${q}`));
    },
    async lessonCheckpoint(
      learnerId: string,
      node: string,
      checkpoint: string,
      answer: string,
    ): Promise<CheckpointResult> {
      return parseCheckpointResult(
        await post(`lessons/${node}/checkpoints`, {
          learner_id: learnerId,
          course: COURSE,
          checkpoint,
          answer,
        }),
      );
    },
    async startPractice(learnerId: string, node: string): Promise<Step> {
      return parseStep(
        await post(`nodes/${node}/practice`, {
          learner_id: learnerId,
          course: COURSE,
        }),
      );
    },
    async answerRun(
      learnerId: string,
      runId: string,
      itemId: string,
      answer: string,
    ): Promise<Step> {
      return parseStep(
        await post(`grammar-runs/${runId}/answers`, {
          learner_id: learnerId,
          item_id: itemId,
          answer,
        }),
      );
    },
    async vocabSession(
      learnerId: string,
      chosen?: Level,
      topic?: string,
    ): Promise<VocabSession> {
      const q = new URLSearchParams({
        learner_id: learnerId,
        list: VOCAB_LIST,
      });
      if (chosen) q.set("level", chosen);
      if (topic) q.set("topic", topic);
      return parseVocabSession(await request(`vocab/session?${q}`));
    },
    async vocabLevels(learnerId: string, topic?: string): Promise<VocabLevels> {
      const q = new URLSearchParams({
        learner_id: learnerId,
        list: VOCAB_LIST,
      });
      if (topic) q.set("topic", topic);
      return parseVocabLevels(await request(`vocab/levels?${q}`));
    },
    async vocabAnswer(
      learnerId: string,
      itemId: string,
      answer: string,
    ): Promise<VocabAnswer> {
      return parseVocabAnswer(
        await post("vocab/answers", {
          learner_id: learnerId,
          item_id: itemId,
          answer,
        }),
      );
    },
    /** A retry in the flashcard test: graded, never scheduled. */
    async vocabCheck(itemId: string, answer: string): Promise<VocabCheck> {
      return parseVocabCheck(
        await post("vocab/checks", { item_id: itemId, answer }),
      );
    },
    async writingPrompts(learnerId: string): Promise<WritingPrompt[]> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseWritingPrompts(await request(`writing/prompts?${q}`));
    },
    async essays(learnerId: string): Promise<EssaySummary[]> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseEssaySummaries(await request(`essays?${q}`));
    },
    async essay(learnerId: string, essayId: string): Promise<Essay> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseEssay(
        await request(`essays/${encodeURIComponent(essayId)}?${q}`),
      );
    },
    /** Sends the essay with the accepted notice version; the API queues it for the worker. */
    async submitEssay(
      learnerId: string,
      promptId: string,
      text: string,
    ): Promise<string> {
      const d = (await post("essays", {
        learner_id: learnerId,
        prompt_id: promptId,
        text,
        consent: CONSENT,
      })) as { essay_id?: unknown };
      if (typeof d?.essay_id !== "string") throw new DataError("contract");
      return d.essay_id;
    },
    /** One self-correction try, or `null` with `showAnswer` to see the correction. */
    async correctSentence(
      learnerId: string,
      essayId: string,
      issueId: number,
      sentence: string | null,
      showAnswer = false,
    ): Promise<CorrectionResult> {
      return parseCorrection(
        await post(`essays/${encodeURIComponent(essayId)}/corrections`, {
          learner_id: learnerId,
          issue_id: issueId,
          sentence,
          show_answer: showAnswer,
        }),
      );
    },
    async requestRewrite(
      learnerId: string,
      essayId: string,
      paragraph: number,
    ): Promise<string> {
      const d = (await post(`essays/${encodeURIComponent(essayId)}/rewrites`, {
        learner_id: learnerId,
        paragraph,
      })) as { rewrite_id?: unknown };
      if (typeof d?.rewrite_id !== "string") throw new DataError("contract");
      return d.rewrite_id;
    },
    async savePhrase(
      learnerId: string,
      rewriteId: string,
      change: number,
    ): Promise<string> {
      const d = (await post("phrases", {
        learner_id: learnerId,
        rewrite_id: rewriteId,
        change,
      })) as { phrase_id?: unknown };
      if (typeof d?.phrase_id !== "string") throw new DataError("contract");
      return d.phrase_id;
    },
    async phraseSession(learnerId: string): Promise<PhraseSession> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parsePhraseSession(await request(`phrases/session?${q}`));
    },
    async answerPhrase(
      learnerId: string,
      phraseId: string,
      answer: string,
    ): Promise<PhraseAnswer> {
      return parsePhraseAnswer(
        await post("phrases/answers", {
          learner_id: learnerId,
          phrase_id: phraseId,
          answer,
        }),
      );
    },
    // Pronunciation (specs/pronunciation/step-3.1.md).
    async pronunciationPrompts(
      learnerId: string,
    ): Promise<PronunciationPrompts> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parsePrompts(await request(`pronunciation/prompts?${q}`));
    },
    async sendRecording(
      learnerId: string,
      promptId: string,
      consent: string,
      keep: boolean,
      wav: ArrayBuffer,
    ): Promise<RecordingResult> {
      const q = new URLSearchParams({
        learner_id: learnerId,
        prompt_id: promptId,
        consent,
        keep: String(keep),
      });
      return parseRecordingResult(
        await request(`recordings?${q}`, {
          method: "POST",
          headers: { "Content-Type": "audio/wav" },
          body: wav,
        }),
      );
    },
    /** The owner's Reading review queue (specs/listening-reading/step-4.2c.md). */
    async readingTexts(learnerId: string): Promise<TextSummary[]> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseTexts(await request(`reading/texts?${q}`));
    },
    async readingText(learnerId: string, slug: string): Promise<ReadingText> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseText(
        await request(`reading/texts/${encodeURIComponent(slug)}?${q}`),
      );
    },
    async startReadingTest(
      learnerId: string,
      slug: string,
    ): Promise<StartedTest> {
      return parseStartedTest(
        await post(`reading/texts/${encodeURIComponent(slug)}/tests`, {
          learner_id: learnerId,
        }),
      );
    },
    async submitReadingTest(
      learnerId: string,
      testId: string,
      answers: ReturnType<typeof submission>,
    ): Promise<TestResult> {
      return parseTestResult(
        await post(`reading/tests/${encodeURIComponent(testId)}/submit`, {
          learner_id: learnerId,
          answers,
        }),
      );
    },
    async answerReading(
      learnerId: string,
      itemId: string,
      answer: Answer,
    ): Promise<AnswerResult> {
      return parseAnswer(
        await post(`reading/items/${encodeURIComponent(itemId)}/answer`, {
          learner_id: learnerId,
          answer,
        }),
      );
    },
    async maps(learnerId: string): Promise<Maps> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseMaps(await request(`maps?${q}`));
    },
    async today(learnerId: string, minutes = 40): Promise<Today> {
      const q = new URLSearchParams({
        learner_id: learnerId,
        minutes: String(minutes),
      });
      return parseToday(await request(`today?${q}`));
    },
    async recheckNext(learnerId: string): Promise<RecheckQuestion | null> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseRecheck(await request(`rechecks/next?${q}`));
    },
    async recheckAnswer(
      learnerId: string,
      id: string,
      answer: string,
    ): Promise<RecheckResult> {
      return parseRecheckResult(
        await post(`rechecks/${encodeURIComponent(id)}/answer`, {
          learner_id: learnerId,
          answer,
        }),
      );
    },
    async readingReview(
      learnerId: string,
      status: ReviewStatus,
    ): Promise<ReviewQueue> {
      const q = new URLSearchParams({ learner_id: learnerId, status });
      return parseQueue(await request(`reading/review?${q}`));
    },
    async reviewTexts(learnerId: string): Promise<ReviewTexts> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseReviewTexts(await request(`reading/review/texts?${q}`));
    },
    async reviewText(learnerId: string, slug: string): Promise<PassageReview> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parsePassageReview(
        await request(`reading/review/texts/${encodeURIComponent(slug)}?${q}`),
      );
    },
    async decideReading(
      learnerId: string,
      itemId: string,
      body: {
        decision: "approve" | "reject";
        reason?: RejectReason;
        note?: string;
        seconds?: number;
      },
    ): Promise<void> {
      const q = new URLSearchParams({ learner_id: learnerId });
      await post(`reading/review/${encodeURIComponent(itemId)}?${q}`, body);
    },
    async recordings(learnerId: string): Promise<RecordingRow[]> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseRecordings(await request(`recordings?${q}`));
    },
    async recording(learnerId: string, id: string): Promise<RecordingDetail> {
      const q = new URLSearchParams({ learner_id: learnerId });
      return parseRecording(
        await request(`recordings/${encodeURIComponent(id)}?${q}`),
      );
    },
    /** The proxied WAV of a kept recording, for the owner's labelling (step 3.3b). */
    recordingAudioUrl(learnerId: string, id: string): string {
      const q = new URLSearchParams({ learner_id: learnerId });
      return `/api/backend/recordings/${encodeURIComponent(id)}/audio?${q}`;
    },
    async saveLabels(
      learnerId: string,
      id: string,
      labels: { target: number; label: Label }[],
    ): Promise<void> {
      const q = new URLSearchParams({ learner_id: learnerId });
      await post(`recordings/${encodeURIComponent(id)}/labels?${q}`, {
        labels,
      });
    },
    async deleteRecording(learnerId: string, id: string): Promise<void> {
      const q = new URLSearchParams({ learner_id: learnerId });
      await request(`recordings/${encodeURIComponent(id)}?${q}`, {
        method: "DELETE",
      });
    },
    async deleteEssay(learnerId: string, essayId: string): Promise<void> {
      const q = new URLSearchParams({ learner_id: learnerId });
      await request(`essays/${encodeURIComponent(essayId)}?${q}`, {
        method: "DELETE",
      });
    },
    async roadmap(learnerId: string): Promise<Roadmap> {
      const q = new URLSearchParams({ learner_id: learnerId, course: COURSE });
      return parseRoadmap(await request(`roadmap?${q}`));
    },
  };
}

export function levelResultOf(step: Step): LevelResult | null {
  return step.finished ? parseLevelResult(step.finished) : null;
}

export type EnglishClient = ReturnType<typeof englishClient>;
