"use client";
import { useEffect, useRef, useState } from "react";
import { englishClient } from "@/lib/english/client";
import { MAX_SECONDS, toServerWav } from "@/lib/pronunciation/wav";
import type {
  Label,
  PronunciationPrompts,
  RecordingDetail,
  RecordingResult,
  RecordingRow,
  Sound,
} from "@/lib/pronunciation/types";
import { vi } from "@/messages/vi";
import { Problem } from "@/components/english/problem";
import { SpeakButton } from "@/components/english/speak-button";
import { useLearner } from "@/components/english/use-learner";

const t = vi.english.pronunciation;
const CONSENT_KEY = "nodetrail_voice_consent";

type Take = { wav: ArrayBuffer; url: string };

/** Reads the decoded channels of a recorded blob; the browser's decoder does the format work. */
async function decode(blob: Blob): Promise<Take> {
  const ctx = new AudioContext();
  try {
    const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
    const channels = Array.from({ length: audio.numberOfChannels }, (_, i) =>
      audio.getChannelData(i),
    );
    const wav = toServerWav(channels, audio.sampleRate);
    return {
      wav,
      url: URL.createObjectURL(new Blob([wav], { type: "audio/wav" })),
    };
  } finally {
    void ctx.close();
  }
}

/** The marked sounds of a recording (step 3.4a): owner only, labelled unverified, never a score. */
function Marks({
  detail,
  sounds,
}: {
  detail: RecordingDetail;
  sounds: Map<string, Sound>;
}) {
  if (detail.marks.length === 0) return <p className="en-muted">{t.noMarks}</p>;
  return (
    <div className="nt-pron-marks" data-testid="recording-marks">
      <p className="en-badge draft">{t.marksTitle}</p>
      <ul>
        {detail.marks.map((i) => {
          const s = detail.targets[i];
          if (!s) return null;
          const sound = sounds.get(s.sound);
          return (
            <li key={i}>
              <u lang="en">{s.word}</u>: {sound?.name_vi ?? s.sound}
              {s.competitor ? ` (${t.heard} /${s.competitor}/)` : ""}
              {sound?.tip_vi && <p className="en-muted">{sound.tip_vi}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const LABEL_ORDER: Label[] = ["right", "wrong", "unsure"];
const PAD_SECONDS = 0.15; // heard either side of the aligned segment

/**
 * One recording's target sounds (step 3.3a/b). A kept recording can be labelled by ear, with its
 * scores hidden until asked for; any other one shows raw scores, never "right" or "wrong".
 */
function Scores({
  learner,
  detail,
  sounds,
  onChange,
}: {
  learner: string;
  detail: RecordingDetail;
  sounds: Map<string, Sound>;
  onChange: (detail: RecordingDetail) => void;
}) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const stopAt = useRef<number | null>(null);
  const [reveal, setReveal] = useState(!detail.keep);
  const [saving, setSaving] = useState(false);
  useEffect(
    () => () => void (stopAt.current && window.clearTimeout(stopAt.current)),
    [],
  );
  if (detail.failed) return <p className="en-muted">{t.failed}</p>;
  const client = englishClient();

  function play(startMs?: number, endMs?: number) {
    const el = audio.current;
    if (!el) return;
    if (stopAt.current) window.clearTimeout(stopAt.current);
    const from =
      startMs === undefined ? 0 : Math.max(0, startMs / 1000 - PAD_SECONDS);
    el.currentTime = from;
    void el.play();
    if (endMs !== undefined)
      stopAt.current = window.setTimeout(
        () => el.pause(),
        (endMs / 1000 + PAD_SECONDS - from) * 1000,
      );
  }

  async function label(target: number, value: Label) {
    setSaving(true);
    try {
      await client.saveLabels(learner, detail.id, [{ target, label: value }]);
      onChange({ ...detail, labels: { ...detail.labels, [target]: value } });
    } finally {
      setSaving(false);
    }
  }

  const done = Object.keys(detail.labels).length;
  return (
    <div data-testid="recording-scores">
      {detail.keep ? (
        <>
          <p className="en-muted">{t.labelIntro}</p>
          <audio
            ref={audio}
            preload="auto"
            src={client.recordingAudioUrl(learner, detail.id)}
          />
          <p>
            <button
              type="button"
              className="en-button ghost small"
              onClick={() => play()}
            >
              {t.playSentence}
            </button>{" "}
            <span className="en-muted">
              {done}/{detail.targets.length} {t.labelled}
            </span>{" "}
            {!reveal && (
              <button
                type="button"
                className="en-button ghost small"
                onClick={() => setReveal(true)}
              >
                {t.showScores}
              </button>
            )}
          </p>
        </>
      ) : (
        <p className="en-muted">{t.labelKeepOnly}</p>
      )}
      {reveal && <Marks detail={detail} sounds={sounds} />}
      {reveal && <p className="en-muted">{t.scoresNote}</p>}
      <table className="nt-pron-scores">
        <thead>
          <tr>
            <th>{t.sound}</th>
            <th>{t.word}</th>
            {detail.keep && <th>{t.play}</th>}
            {detail.keep && <th>{t.labelled}</th>}
            {reveal && <th>{t.score}</th>}
            {reveal && <th>{t.heardAs}</th>}
          </tr>
        </thead>
        <tbody>
          {detail.targets.map((s, i) => (
            <tr key={i}>
              <td>
                {sounds.get(s.sound)?.name_vi ?? s.sound} /{s.phone}/
              </td>
              <td lang="en">{s.word}</td>
              {detail.keep && (
                <td>
                  <button
                    type="button"
                    className="en-button ghost small"
                    aria-label={`${t.play} ${s.word}`}
                    onClick={() => play(s.start_ms, s.end_ms)}
                  >
                    ▶
                  </button>
                </td>
              )}
              {detail.keep && (
                <td className="nt-pron-labels">
                  {LABEL_ORDER.map((value) => (
                    <button
                      key={value}
                      type="button"
                      className="en-button ghost small"
                      aria-pressed={detail.labels[i] === value}
                      disabled={saving}
                      onClick={() => void label(i, value)}
                    >
                      {t.labels[value]}
                    </button>
                  ))}
                </td>
              )}
              {reveal && <td>{s.gop.toFixed(2)}</td>}
              {reveal && <td>{s.competitor ? `/${s.competitor}/` : "—"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Steps 3.1 and 3.3a (specs/pronunciation): read a sentence aloud; quality check, then raw scores per sound. */
export function PronunciationPage() {
  const { learner, error: learnerError, retry } = useLearner();
  const [data, setData] = useState<PronunciationPrompts | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [index, setIndex] = useState(0);
  const [consented, setConsented] = useState(() => {
    try {
      return (
        typeof window !== "undefined" &&
        window.localStorage.getItem(CONSENT_KEY) === "voice-v1"
      );
    } catch {
      return false;
    }
  });
  const [keep, setKeep] = useState(false);
  const [recording, setRecording] = useState(false);
  const [take, setTake] = useState<Take | null>(null);
  const [result, setResult] = useState<RecordingResult | null>(null);
  const [rows, setRows] = useState<RecordingRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const [open, setOpen] = useState<RecordingDetail | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!learner) return;
    let live = true;
    const client = englishClient();
    client
      .pronunciationPrompts(learner)
      .then((d) => {
        if (!live) return;
        setData(d);
        if (d.can_record)
          void client.recordings(learner).then((r) => live && setRows(r));
      })
      .catch((e: unknown) => live && setError(e));
    return () => {
      live = false;
    };
  }, [learner]);

  useEffect(
    () => () => void (timer.current && window.clearTimeout(timer.current)),
    [],
  );

  if (learnerError) return <Problem error={learnerError} onRetry={retry} />;
  if (error) return <Problem error={error} />;
  if (!data || !learner)
    return <p className="en-muted">{vi.english.loading}</p>;
  const prompt = data.prompts[index % data.prompts.length]!;
  const soundsById = new Map(data.sounds.map((s) => [s.id, s]));
  const sounds = prompt.targets.map((id) => soundsById.get(id)?.name_vi ?? id);

  async function start() {
    setResult(null);
    setTake(null);
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
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      void decode(new Blob(chunks, { type: rec.mimeType }))
        .then(setTake)
        .catch(() =>
          setResult({
            ok: false,
            problems: ["format"],
            id: null,
            delete_after: null,
          }),
        );
    };
    recorder.current = rec;
    rec.start();
    setRecording(true);
    timer.current = window.setTimeout(
      () => rec.state === "recording" && rec.stop(),
      MAX_SECONDS * 1000,
    );
  }

  function stop() {
    if (timer.current) window.clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  async function send() {
    if (!take) return;
    setBusy(true);
    try {
      const client = englishClient();
      const r = await client.sendRecording(
        learner!,
        prompt.id,
        data!.consent,
        keep,
        take.wav,
      );
      setResult(r);
      if (r.id) setRows(await client.recordings(learner!));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  async function show(id: string) {
    if (open?.id === id) return setOpen(null);
    try {
      setOpen(await englishClient().recording(learner!, id));
    } catch (e) {
      setError(e);
    }
  }

  async function remove(id: string) {
    await englishClient().deleteRecording(learner!, id);
    setRows((r) => r.filter((x) => x.id !== id));
  }

  return (
    <>
      <section className="en-card nt-pron" data-testid="pronunciation">
        <h1>{t.title}</h1>
        <p className="en-muted">{t.intro}</p>
        <div className="nt-pron-prompt">
          <p className="en-muted">
            {t.sentence} · {prompt.level}
          </p>
          <p className="nt-pron-text" lang="en">
            {prompt.text} <SpeakButton text={prompt.text} />
          </p>
          <p className="en-muted">
            {t.targets}: {sounds.join(" · ")}
          </p>
        </div>

        {!data.can_record ? (
          <p className="en-badge draft">{t.ownerOnly}</p>
        ) : !consented ? (
          <div className="nt-pron-consent">
            <p>{t.consent}</p>
            <label>
              <input
                type="checkbox"
                onChange={(e) => {
                  if (!e.target.checked) return;
                  setConsented(true);
                  try {
                    window.localStorage.setItem(CONSENT_KEY, data.consent);
                  } catch {
                    // asked again next time
                  }
                }}
              />{" "}
              {t.consentAgree}
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
            <div className="nt-actions">
              {recording ? (
                <button type="button" className="en-button" onClick={stop}>
                  {t.stop}
                </button>
              ) : (
                <button
                  type="button"
                  className="en-button"
                  onClick={() => void start()}
                >
                  {take ? t.again : t.record}
                </button>
              )}
              {take && !recording && (
                <button
                  type="button"
                  className="en-button ghost"
                  disabled={busy}
                  onClick={() => void send()}
                >
                  {t.send}
                </button>
              )}
              <button
                type="button"
                className="en-button ghost"
                onClick={() => {
                  setIndex((i) => i + 1);
                  setTake(null);
                  setResult(null);
                }}
              >
                {t.next}
              </button>
            </div>
            {recording && <p className="nt-pron-live">{t.recording}</p>}
            {noMic && <p className="en-feedback is-wrong">{t.noMic}</p>}
            {take && (
              <p>
                {t.yours}: <audio controls src={take.url} />
              </p>
            )}
            {result && (
              <div
                className={`en-feedback ${result.ok ? "is-right" : "is-wrong"}`}
                role="status"
              >
                {result.ok ? (
                  <p>
                    {t.ok}{" "}
                    {result.delete_after
                      ? `${t.okUntil} ${new Date(result.delete_after).toLocaleString("vi-VN")}.`
                      : t.kept}
                  </p>
                ) : (
                  result.problems.map((p) => (
                    <p key={p}>{t.problems[p] ?? p}</p>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </section>
      {data.can_record && data.progress.length > 0 && (
        <section className="en-card" data-testid="pronunciation-progress">
          <h2>{t.progressTitle}</h2>
          <p className="en-muted">{t.progressNote}</p>
          <ul className="nt-pron-rows">
            {data.progress.map((n) => (
              <li key={n.node}>
                <span>{n.name_vi}</span>
                <span className="en-muted">
                  {!n.measured
                    ? t.progressNotMeasured
                    : n.p_known === null
                      ? t.progressNoData
                      : n.known
                        ? t.progressKnown
                        : t.progressLearning}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {data.can_record && (
        <section className="en-card">
          <h2>{t.list}</h2>
          {rows.length === 0 ? (
            <p className="en-muted">{t.none}</p>
          ) : (
            <ul className="nt-pron-rows">
              {rows.map((r) => (
                <li key={r.id}>
                  <span>
                    {r.prompt_id} · {r.seconds.toFixed(1)} {t.seconds}
                    {r.delete_after
                      ? ` · ${t.okUntil} ${new Date(r.delete_after).toLocaleString("vi-VN")}`
                      : ` · ${t.kept}`}
                    {r.status === "stored" && ` · ${t.waiting}`}
                  </span>
                  {r.status !== "stored" && (
                    <button
                      type="button"
                      className="en-button ghost small"
                      onClick={() => void show(r.id)}
                    >
                      {open?.id === r.id ? t.hide : t.show}
                    </button>
                  )}
                  <button
                    type="button"
                    className="en-button ghost small"
                    onClick={() => void remove(r.id)}
                  >
                    {t.delete}
                  </button>
                  {open?.id === r.id && (
                    <Scores
                      key={open.id}
                      learner={learner}
                      detail={open}
                      sounds={soundsById}
                      onChange={setOpen}
                    />
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}
