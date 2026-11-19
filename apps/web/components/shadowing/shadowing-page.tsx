"use client";
import { useState } from "react";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { BankTab } from "./bank-tab";
import { VideoTab } from "./video-tab";

const t = vi.english.shadowing;
type Tab = "bank" | "video";

/** Shadowing: the bank's sentences or any YouTube video, recorded in the browser only (step 4.4d). */
export function ShadowingPage() {
  const { learner, error, retry } = useLearner();
  const [tab, setTab] = useState<Tab>("bank");
  if (error) return <Problem error={error} onRetry={retry} />;
  if (!learner) return <p className="en-muted">{vi.english.loading}</p>;
  return (
    <section className="en-card nt-review" data-testid="shadowing">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      <div className="nt-actions" role="tablist">
        {(["bank", "video"] as const).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            className={`en-button small ${tab === k ? "" : "ghost"}`}
            onClick={() => setTab(k)}
          >
            {t.tabs[k]}
          </button>
        ))}
      </div>
      {tab === "bank" ? <BankTab learner={learner} /> : <VideoTab />}
    </section>
  );
}
