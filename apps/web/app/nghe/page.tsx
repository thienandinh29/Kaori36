import { EnglishShell } from "@/components/english/shell";
import { ListeningList } from "@/components/listening/listening-list";

/** Listening practice: texts with dictation and gap-fill (specs/listening-reading/step-4.4b.md). */
export default function Page() {
  return (
    <EnglishShell active="/nghe">
      <ListeningList />
    </EnglishShell>
  );
}
