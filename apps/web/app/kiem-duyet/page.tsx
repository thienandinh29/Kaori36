import type { Metadata } from "next";
import { ReviewPortal } from "@/components/review/portal-client";

export const metadata: Metadata = {
  title: "Kiểm tra nội dung · NodeTrail",
  robots: { index: false, follow: false },
};

/** The private reviewer portal (specs/validation/step-v2.md); no learner navigation. */
export default function Page() {
  return (
    <div className="en-shell">
      <main className="en-main">
        <ReviewPortal />
      </main>
    </div>
  );
}
