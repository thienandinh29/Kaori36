import type { Feedback as FeedbackData } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { Sena } from "@/components/sena/sena";

const t = vi.english;

/** Right or wrong, the right answer, and the mistake explained in Vietnamese (specs/web-english, 4). */
export function Feedback({ feedback }: { feedback: FeedbackData }) {
  return (
    <div
      className={`en-feedback has-sena ${feedback.correct ? "is-right" : "is-wrong"}`}
      role="status"
    >
      <Sena
        pose={feedback.correct ? "idle" : "oops"}
        label={feedback.correct ? t.senaSays.right : t.senaSays.wrong}
      />
      <div>
        <strong>{feedback.correct ? t.run.right : t.run.wrong}</strong>
        {!feedback.correct && (
          <p>
            {t.run.answerWas}: <b lang="en">{feedback.key}</b>
          </p>
        )}
        {feedback.misconception_vi && <p>{feedback.misconception_vi}</p>}
      </div>
    </div>
  );
}
