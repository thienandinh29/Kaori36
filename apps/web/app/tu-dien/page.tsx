import { Dictionary } from "@/components/english/dictionary";
import { EnglishShell } from "@/components/english/shell";

export default function Page() {
  return (
    <EnglishShell active="/tu-dien">
      <Dictionary />
    </EnglishShell>
  );
}
