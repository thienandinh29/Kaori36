import { EnglishShell } from "@/components/english/shell";
import { PracticePage } from "@/components/speaking/practice-page";

/** Guided Speaking practice (specs/speaking/step-5.4b.md). */
export default function Page() {
  return (
    <EnglishShell active="/noi/luyen">
      <PracticePage />
    </EnglishShell>
  );
}
