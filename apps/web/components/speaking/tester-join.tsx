"use client";
import Link from "next/link";
import { useState } from "react";
import { Problem } from "@/components/english/problem";
import { englishClient } from "@/lib/english/client";
import {
  LEARNER_KEY,
  browserStore,
  storedLearner,
} from "@/lib/english/learner";
import { CONSENT_KEY } from "@/lib/speaking/exam";
import type { Joined } from "@/lib/speaking/tester";
import { DataError } from "@/lib/decode";
import { vi } from "@/messages/vi";

const t = vi.english.tester;
const notice = vi.english.speakingTest;

/** An invited tester opens the link (specs/speaking/step-5.5.md). The link is used by the button,
 *  not by loading the page: messengers preview links and would spend it. */
export function TesterJoin({ token }: { token: string }) {
  const [research, setResearch] = useState(false);
  const [state, setState] = useState<"ready" | "joining" | "bad" | "done">(
    "ready",
  );
  const [joined, setJoined] = useState<Joined | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [replaces] = useState(() => {
    const known = storedLearner(browserStore());
    return known !== null;
  });

  async function join() {
    setState("joining");
    try {
      const client = englishClient();
      const j = await client.redeemInvite(token);
      if (research) await client.acceptResearchNotice(j.research_notice);
      try {
        window.localStorage.setItem(LEARNER_KEY, j.learner_id);
        // the notice above is the Speaking notice they just read
        window.localStorage.setItem(CONSENT_KEY, "speaking-v1");
      } catch {
        // remembered for this page only
      }
      setJoined(j);
      setState("done");
    } catch (e) {
      if (e instanceof DataError && e.status === 404) setState("bad");
      else {
        setError(e);
        setState("ready");
      }
    }
  }

  if (error) return <Problem error={error} />;
  if (state === "bad")
    return (
      <section className="en-card nt-exam" data-testid="join-bad">
        <h1>{t.joinTitle}</h1>
        <p className="en-feedback is-wrong">{t.badLink}</p>
      </section>
    );
  if (state === "done" && joined)
    return (
      <section className="en-card nt-exam" data-testid="join-done">
        <h1>{t.joinTitle}</h1>
        <p>{t.joined}</p>
        {!joined.may_record && <p className="en-badge draft">{t.closed}</p>}
        <div className="nt-actions">
          <Link className="en-button" href="/noi/thi">
            {t.goExam}
          </Link>
          <Link className="en-button secondary" href="/noi/luyen">
            {t.goPractice}
          </Link>
        </div>
      </section>
    );
  return (
    <section className="en-card nt-exam" data-testid="join">
      <h1>{t.joinTitle}</h1>
      <p>{t.joinIntro("bạn")}</p>
      <p className="en-muted">{t.keepNotice}</p>
      <div className="nt-pron-consent">
        <p>{notice.consent}</p>
      </div>
      <h2>{t.researchTitle}</h2>
      <p className="en-badge draft">{t.researchDraft}</p>
      <p className="en-muted">{t.researchText}</p>
      <label className="nt-pron-keep">
        <input
          type="checkbox"
          checked={research}
          onChange={(e) => setResearch(e.target.checked)}
        />{" "}
        {t.researchAgree}
      </label>
      {replaces && <p className="en-feedback is-wrong">{t.otherAccount}</p>}
      <div className="nt-actions">
        <button
          type="button"
          className="en-button"
          disabled={state === "joining"}
          onClick={() => void join()}
        >
          {state === "joining" ? t.joining : t.start}
        </button>
      </div>
    </section>
  );
}
