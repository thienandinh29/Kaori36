import { EnglishShell } from "@/components/english/shell";
import { TwoMaps } from "@/components/english/two-maps";

/** The two maps: IELTS competencies over CEFR foundations (specs/two-layer-map, M4). */
export default function Page() {
  return (
    <EnglishShell active="/ban-do">
      <TwoMaps />
    </EnglishShell>
  );
}
