import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { LessonPage } from "@/components/lesson/lesson-player";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** A lesson before practice (specs/grammar-lessons): /hoc/<node>. */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!SLUG.test(slug)) notFound();
  return (
    <EnglishShell active="/lo-trinh">
      <LessonPage node={slug} />
    </EnglishShell>
  );
}
