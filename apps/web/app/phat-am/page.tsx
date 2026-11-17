import { EnglishShell } from "@/components/english/shell";
import { PronunciationPage } from "@/components/pronunciation/pronunciation-page";

/** Pronunciation practice (specs/pronunciation/step-3.1.md). */
export default function Page() {
  return (
    <EnglishShell active="/phat-am">
      <PronunciationPage />
    </EnglishShell>
  );
}
