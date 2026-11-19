import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { ReadingPractice } from "@/components/reading/reading-practice";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** One Reading text and its questions (specs/listening-reading/step-4.3.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!SLUG.test(slug)) notFound();
  return (
    <EnglishShell active="/doc">
      <ReadingPractice slug={slug} />
    </EnglishShell>
  );
}
