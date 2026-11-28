import { notFound } from "next/navigation";
import { EnglishShell } from "@/components/english/shell";
import { TesterJoin } from "@/components/speaking/tester-join";
import { inviteToken } from "@/lib/speaking/tester";

/** An invited tester's link (specs/speaking/step-5.5.md); used by the button on the page. */
export default async function Page({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const valid = inviteToken(token);
  if (valid === null) notFound();
  return (
    <EnglishShell active="/noi/thi">
      <TesterJoin token={valid} />
    </EnglishShell>
  );
}
