import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { PassagePractice } from "@/components/listening/passage-practice";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Listen to a whole passage, then answer (specs/listening-reading/step-4.4c.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!SLUG.test(slug)) notFound();
  return (
    <EnglishShell active="/nghe">
      <PassagePractice slug={slug} />
    </EnglishShell>
  );
}
