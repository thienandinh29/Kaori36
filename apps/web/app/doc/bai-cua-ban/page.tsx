import { EnglishShell } from "@/components/english/shell";
import { OwnTestPage } from "@/components/reading/own-test";

/** A Reading test taken outside the app, pasted for feedback (specs/listening-reading/step-4.3d.md). */
export default function Page() {
  return (
    <EnglishShell active="/doc">
      <OwnTestPage />
    </EnglishShell>
  );
}
