import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { ReadingTest } from "@/components/reading/reading-test";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** A timed test on one Reading text (specs/listening-reading/step-4.3b.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!SLUG.test(slug)) notFound();
  return (
    <EnglishShell active="/doc">
      <ReadingTest slug={slug} />
    </EnglishShell>
  );
}
