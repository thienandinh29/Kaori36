import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { ListeningPractice } from "@/components/listening/listening-practice";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** One text's listening exercises (specs/listening-reading/step-4.4b.md). */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!SLUG.test(slug)) notFound();
  return (
    <EnglishShell active="/nghe">
      <ListeningPractice slug={slug} />
    </EnglishShell>
  );
}
