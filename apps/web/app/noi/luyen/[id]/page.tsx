import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { PracticeView } from "@/components/speaking/practice-view";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

/** One practised question: the try to speak, or the tries so far (specs/speaking/step-5.4b.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!UUID.test(id)) notFound();
  return (
    <EnglishShell active="/noi/luyen">
      <PracticeView tryId={id} />
    </EnglishShell>
  );
}
