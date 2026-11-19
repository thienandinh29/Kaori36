"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import type { Focus } from "@/lib/english/say-word";
import { vi } from "@/messages/vi";
import { SpeakButton } from "@/components/english/speak-button";

const t = vi.english.sayFocus;

/** The sounds the learner most often misses when saying words (step 3.7b); owner's own data. */
export function SayFocus({ learner }: { learner: string }) {
  const [focus, setFocus] = useState<Focus | null>(null);
  useEffect(() => {
    let live = true;
    englishClient()
      .sayFocus(learner)
      .then((f) => live && setFocus(f))
      .catch(() => live && setFocus(null));
    return () => {
      live = false;
    };
  }, [learner]);
  if (!focus) return null;
  return (
    <section className="en-card" data-testid="say-focus">
      <h2>{t.title}</h2>
      {focus.sounds.length === 0 ? (
        <p className="en-muted">{t.none}</p>
      ) : (
        <>
          <p className="en-muted">{t.intro(focus.days, focus.attempts)}</p>
          <ol className="nt-focus">
            {focus.sounds.map((s) => (
              <li key={s.phone}>
                <strong lang="en-fonipa">
                  {t.row(s.phone, s.low, s.seen)}
                </strong>
                {s.heard && (
                  <span className="en-muted"> · {t.heard(s.heard)}</span>
                )}
                {s.how && <p>{s.how}</p>}
                {s.example && (
                  <p lang="en">
                    {t.example}: {s.example} <SpeakButton text={s.example} />
                  </p>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
