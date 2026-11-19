import { EnglishShell } from "@/components/english/shell";
import { ReadingList } from "@/components/reading/reading-list";

/** Reading practice: the texts with questions ready (specs/listening-reading/step-4.3.md). */
export default function Page() {
  return (
    <EnglishShell active="/doc">
      <ReadingList />
    </EnglishShell>
  );
}
