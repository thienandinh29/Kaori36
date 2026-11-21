import { notFound } from "next/navigation";
import { EssayEditor } from "@/components/english/essay-editor";
import { EnglishShell } from "@/components/english/shell";

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ prompt: string }>;
  searchParams: Promise<{ thi?: string }>;
}) {
  const { prompt } = await params;
  const { thi } = await searchParams;
  if (!SLUG.test(prompt) || prompt.length > 40) notFound();
  return (
    <EnglishShell active="/viet">
      <EssayEditor promptId={prompt} exam={thi === "1"} />
    </EnglishShell>
  );
}
