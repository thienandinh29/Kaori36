"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Problem } from "@/components/english/problem";
import { useLearner } from "@/components/english/use-learner";
import { englishClient } from "@/lib/english/client";
import { CONSENT_KEY, type Overview } from "@/lib/speaking/exam";
import { vi } from "@/messages/vi";

const t = vi.english.speakingPractice;
const notice = vi.english.speakingTest;

function consented(): boolean {
  try {
    return window.localStorage.getItem(CONSENT_KEY) === "speaking-v1";
  } catch {
    return false;
  }
}

/** Guided practice (specs/speaking/step-5.4b.md), owner only: pick one question to practise. */
export function PracticePage() {
  const router = useRouter();
  const { learner, error: learnerError, retry } = useLearner();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [agreed, setAgreed] = useState(
    () => typeof window !== "undefined" && consented(),
  );
  const [keep, setKeep] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .speakingTests(learner)
      .then((o) => live && setOverview(o))
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!overview || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;

  async function start(testId: string, questionId: string) {
    setBusy(true);
    try {
      const made = await englishClient().startSpeakingPractice(learner!, {
        testId,
        questionId,
        consent: overview!.consent,
        keep,
        previousId: null,
      });
      router.push(`/noi/luyen/${made.id}`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  }

  return (
    <section className="en-card nt-exam" data-testid="speaking-practice">
      <h1>{t.title}</h1>
      <p className="en-muted">{t.intro}</p>
      {overview.left_today && (
        <p className="en-muted small" data-testid="left-today">
          {vi.english.tester.leftToday(
            overview.left_today.mock_tests,
            overview.left_today.practice_tries,
          )}
        </p>
      )}
      {!overview.can_record ? (
        <p className="en-badge draft">{t.ownerOnly}</p>
      ) : !agreed ? (
        <div className="nt-pron-consent">
          <p>{notice.consent}</p>
          <label>
            <input
              type="checkbox"
              onChange={(e) => {
                if (!e.target.checked) return;
                setAgreed(true);
                try {
                  window.localStorage.setItem(CONSENT_KEY, overview.consent);
                } catch {
                  // asked again next time
                }
              }}
            />{" "}
            {notice.consentAgree}
          </label>
        </div>
      ) : (
        <>
          <label className="nt-pron-keep">
            <input
              type="checkbox"
              checked={keep}
              onChange={(e) => setKeep(e.target.checked)}
            />{" "}
            {t.keep}
          </label>
          <h2>{t.pick}</h2>
          {overview.tests.map((test) => (
            <details key={test.id} className="nt-exam-pick">
              <summary>
                <strong lang="en">{test.title}</strong>{" "}
                {test.draft && (
                  <span className="en-badge draft">{vi.english.draft}</span>
                )}
              </summary>
              <ul className="nt-exam-tests">
                {test.practice.map((q) => (
                  <li key={q.id}>
                    <span>
                      <span className="en-muted small">
                        {t.part(q.part)} · {t.secondsLabel(q.seconds)}
                      </span>
                      <br />
                      <span lang="en">{q.text}</span>
                    </span>
                    <button
                      type="button"
                      className="en-button small"
                      disabled={busy}
                      onClick={() => void start(test.id, q.id)}
                    >
                      {t.start}
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
          <h2>{t.practised}</h2>
          {overview.practices.length === 0 ? (
            <p className="en-muted">{t.noneYet}</p>
          ) : (
            <ul className="nt-exam-past" data-testid="practised">
              {overview.practices.map((p) => (
                <li key={p.id}>
                  <Link href={`/noi/luyen/${p.id}`}>
                    <span lang="en">{p.question}</span>
                  </Link>{" "}
                  <span className="en-muted small">
                    {t.triesOf(p.tries, overview.max_tries)} ·{" "}
                    {new Date(p.started_at).toLocaleString("vi-VN")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
