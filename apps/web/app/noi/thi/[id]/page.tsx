import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { ExamResult } from "@/components/speaking/exam-result";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** A Speaking test replayed (specs/speaking/step-5.4a.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  return (
    <EnglishShell active="/noi/thi">
      <ExamResult sittingId={id} />
    </EnglishShell>
  );
}
