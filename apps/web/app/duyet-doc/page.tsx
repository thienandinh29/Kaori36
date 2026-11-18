import { EnglishShell } from "@/components/english/shell";
import { ReadingReviewPage } from "@/components/reading/review-page";

/** The owner's review queue for Reading questions (specs/listening-reading/step-4.2c.md). */
export default function Page() {
  return (
    <EnglishShell>
      <ReadingReviewPage />
    </EnglishShell>
  );
}
