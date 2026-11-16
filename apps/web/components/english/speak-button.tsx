"use client";
import { Snail, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  RATES,
  canSpeak,
  pickVoice,
  serverAudio,
  serverVoiceAvailable,
  speakable,
  type Pace,
} from "@/lib/english/speech";
import { vi } from "@/messages/vi";

const t = vi.english.speech;

// Asked once per page load; every button shares the answer.
let serverVoice: Promise<boolean> | null = null;
// Recently heard audio, so a word played again is not fetched again.
const played = new Map<string, string>();

/**
 * Speaks English text (specs/speech). The self-hosted voice (S2) is used when the server has one;
 * otherwise, or if it fails, the browser's voice (S1). `private` text (from the learner's own work)
 * may use the self-hosted voice, never a browser voice that sends text to a network service.
 * Renders nothing until one of the two can speak.
 */
export function SpeakButton({
  text,
  private: isPrivate = false,
}: {
  text: string;
  private?: boolean;
}) {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [server, setServer] = useState(false);
  const words = speakable(text);

  useEffect(() => {
    if (!words) return;
    let live = true;
    serverVoice ??= serverVoiceAvailable();
    void serverVoice.then((ok) => live && setServer(ok));
    if (!canSpeak(window)) return () => void (live = false);
    const synth = window.speechSynthesis;
    const choose = () => {
      const best = pickVoice(synth.getVoices(), !isPrivate);
      setVoice((best as SpeechSynthesisVoice | null) ?? null);
    };
    choose();
    synth.addEventListener("voiceschanged", choose);
    return () => {
      live = false;
      synth.removeEventListener("voiceschanged", choose);
    };
  }, [words, isPrivate]);

  if (!words || (!server && !voice)) return null;

  const browserSay = (pace: Pace) => {
    if (!voice) return;
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(words);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = RATES[pace];
    synth.speak(u);
  };

  const say = async (pace: Pace) => {
    if (!server) return browserSay(pace);
    const key = `${pace}|${words}`;
    try {
      let url = played.get(key);
      if (!url) {
        url = URL.createObjectURL(await serverAudio(words, pace));
        played.set(key, url);
        if (played.size > 100) {
          const [oldest, old] = played.entries().next().value as [
            string,
            string,
          ];
          URL.revokeObjectURL(old);
          played.delete(oldest);
        }
      }
      await new Audio(url).play();
    } catch {
      browserSay(pace);
    }
  };

  return (
    <span className="nt-speak" title={server ? t.serverVoice : t.machineVoice}>
      <button
        type="button"
        aria-label={`${t.listen}: ${words}`}
        onClick={() => void say("normal")}
      >
        <Volume2 aria-hidden size={18} />
      </button>
      <button
        type="button"
        aria-label={`${t.listenSlow}: ${words}`}
        onClick={() => void say("slow")}
      >
        <Snail aria-hidden size={18} />
      </button>
    </span>
  );
}
