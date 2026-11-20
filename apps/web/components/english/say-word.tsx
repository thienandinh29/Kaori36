"use client";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  hue,
  type Guide,
  type PhoneResult,
  type SayResult,
  type SayStatus,
} from "@/lib/english/say-word";
import { toServerWav } from "@/lib/pronunciation/wav";
import { vi } from "@/messages/vi";
import { SpeakButton } from "./speak-button";
import { useLearner } from "./use-learner";

const t = vi.english.sayWord;
const CONSENT_KEY = "nodetrail_say_consent";
const MAX_MS = 5000;

function consented(): boolean {
  try {
    return localStorage.getItem(CONSENT_KEY) === "voice-v1";
  } catch {
    return false;
  }
}

/**
 * Say the word aloud (step 3.7): everyone can record and compare with the model by ear (nothing
 * leaves the browser); the owner, with the pronunciation service on, also sees each sound's raw
 * score. The audio sent for analysis is never stored.
 */
export function SayWord({ lemma, pos }: { lemma: string; pos: string }) {
  const { learner } = useLearner();
  const [status, setStatus] = useState<SayStatus | null>(null);
  // Read once on first render; it only matters after a take exists (never in the server's HTML).
  const [agreed, setAgreed] = useState(consented);
  const [recording, setRecording] = useState(false);
  // `id` names this recording: analysing it again replaces its attempt instead of adding one.
  const [take, setTake] = useState<{
    url: string;
    wav: ArrayBuffer;
    id: string;
  } | null>(null);
  const [result, setResult] = useState<SayResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);
  // Analyse as soon as the take is ready when the owner already agreed (step 3.7c: one tap less).
  const auto = useRef(false);
  useEffect(() => {
    auto.current = Boolean(status?.analysis && agreed);
  }, [status, agreed]);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .sayStatus(learner)
      .then((s) => live && setStatus(s))
      .catch(() => live && setStatus(null));
    return () => {
      live = false;
    };
  }, [learner]);
  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
      if (take) URL.revokeObjectURL(take.url);
    },
    [take],
  );

  async function start() {
    setResult(null);
    setNoMic(false);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setNoMic(true);
      return;
    }
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      void (async () => {
        const ctx = new AudioContext();
        try {
          const audio = await ctx.decodeAudioData(
            await new Blob(chunks, { type: rec.mimeType }).arrayBuffer(),
          );
          const channels = Array.from(
            { length: audio.numberOfChannels },
            (_, i) => audio.getChannelData(i),
          );
          const wav = toServerWav(channels, audio.sampleRate);
          const id = crypto.randomUUID();
          setTake({
            wav,
            id,
            url: URL.createObjectURL(new Blob([wav], { type: "audio/wav" })),
          });
          if (auto.current) void analyse(wav, id);
        } catch {
          setResult({
            ok: false,
            problems: ["format"],
            phones: [],
            heard: [],
            guide: [],
          });
        } finally {
          void ctx.close();
        }
      })();
    };
    recorder.current = rec;
    rec.start();
    setRecording(true);
    timer.current = window.setTimeout(
      () => rec.state === "recording" && rec.stop(),
      MAX_MS,
    );
  }
  function stop() {
    if (timer.current) window.clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
  }
  async function analyse(
    wav: ArrayBuffer | undefined = take?.wav,
    id: string | undefined = take?.id,
  ) {
    if (!wav || !id || !learner || !status) return;
    setBusy(true);
    try {
      setResult(
        await englishClient().sayWord(
          learner,
          `${lemma}:${pos}`,
          status.consent,
          wav,
          id,
        ),
      );
    } catch {
      setResult({
        ok: false,
        problems: ["not_analysed"],
        phones: [],
        heard: [],
        guide: [],
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="nt-say" data-testid="say-word">
      <div className="nt-actions">
        {recording ? (
          <button type="button" className="en-button small" onClick={stop}>
            {t.stop}
          </button>
        ) : (
          <button
            type="button"
            className="en-button small ghost"
            onClick={() => void start()}
          >
            {t.say}
          </button>
        )}
        {recording && (
          <span className="en-muted" role="status">
            {t.recording}
          </span>
        )}
      </div>
      {noMic && <p className="en-feedback is-wrong">{t.noMic}</p>}
      {take && (
        <div>
          <p>
            {t.yours}: <audio controls src={take.url} />
          </p>
          {status?.analysis &&
            (agreed ? (
              <button
                type="button"
                className="en-button small"
                disabled={busy}
                onClick={() => void analyse()}
              >
                {busy ? t.analysing : result ? t.again : t.analyse}
              </button>
            ) : (
              <div className="en-feedback">
                <p>{t.consent}</p>
                <button
                  type="button"
                  className="en-button small"
                  onClick={() => {
                    try {
                      localStorage.setItem(CONSENT_KEY, "voice-v1");
                    } catch {
                      /* the choice holds for this page only */
                    }
                    setAgreed(true);
                    void analyse();
                  }}
                >
                  {t.agree}
                </button>
              </div>
            ))}
          {status && !status.analysis && (
            <p className="en-muted">
              {status.owner ? t.serviceOff : t.compare}
            </p>
          )}
        </div>
      )}
      {result && (
        <div role="status" data-testid="say-result">
          {result.ok ? (
            <SayOutcome result={result} />
          ) : (
            <p className="en-feedback is-wrong">
              {result.problems.map((p) => t.problems[p] ?? p).join(" ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/** The word's sounds as one IPA line, each coloured red to green by closeness; tap for details. */
function SayOutcome({ result }: { result: SayResult }) {
  const [picked, setPicked] = useState<number | null>(null);
  const phone: PhoneResult | null =
    picked === null ? null : (result.phones[picked] ?? null);
  return (
    <>
      <p className="nt-ipa-colour" lang="en-fonipa" aria-label={t.ipaLabel}>
        /
        {result.phones.map((p, i) => (
          <button
            key={i}
            type="button"
            className={`nt-ipa-phone${p.dropped ? " is-dropped" : ""}${picked === i ? " is-picked" : ""}`}
            style={{
              color: `hsl(${hue(p.dropped ? 0 : p.closeness)} 75% 34%)`,
            }}
            title={`${p.phone}: ${p.dropped ? t.dropped : p.closeness}`}
            aria-label={`${p.phone}: ${p.dropped ? t.dropped : `${p.closeness}/100`}`}
            onClick={() => setPicked((x) => (x === i ? null : i))}
          >
            {p.phone}
          </button>
        ))}
        /
      </p>
      <p className="en-muted nt-ipa-legend">
        <span className="nt-legend-bar" aria-hidden="true" /> {t.legend}
      </p>
      {phone && (
        <div className="nt-phone-detail" data-testid="phone-detail">
          <p>
            <strong lang="en-fonipa">/{phone.phone}/</strong>{" "}
            {phone.dropped ? t.dropped : `${phone.closeness}/100`}
            {phone.heard && !phone.dropped && (
              <>
                {" "}
                · {t.heard} <span lang="en-fonipa">/{phone.heard}/</span>
              </>
            )}
          </p>
          {phone.how && <p>{phone.how}</p>}
        </div>
      )}
      {result.guide.map((g) => (
        <GuideCard key={g.index} g={g} />
      ))}
      <p className="en-muted">{t.rawNote}</p>
    </>
  );
}

/** The same sound low in 2 of the last 3 tries: what to change, and a pair to hear (step 3.7b). */
function GuideCard({ g }: { g: Guide }) {
  return (
    <div className="en-feedback nt-guide" data-testid="say-guide">
      <p>
        <strong>
          {g.dropped
            ? t.guideDropped(g.phone, g.times, g.of)
            : t.guideHeard(g.phone, g.heard, g.times, g.of)}
        </strong>
      </p>
      {g.change && <p>{g.change}</p>}
      {g.how && (
        <p>
          {t.howTo(g.phone)} {g.how}
        </p>
      )}
      {g.minimal && (
        <p lang="en">
          {t.minimal}: <strong>{g.minimal[0]}</strong>{" "}
          <SpeakButton text={g.minimal[0]} /> · {g.minimal[1]}{" "}
          <SpeakButton text={g.minimal[1]} />
        </p>
      )}
      <p className="en-muted">{t.draft}</p>
    </div>
  );
}
