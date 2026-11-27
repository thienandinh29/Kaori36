import { EnglishShell } from "@/components/english/shell";
import { ExamPage } from "@/components/speaking/exam-page";

/** The Speaking examiner test (specs/speaking/step-5.4a.md). */
export default function Page() {
  return (
    <EnglishShell active="/noi/thi">
      <ExamPage />
    </EnglishShell>
  );
}
