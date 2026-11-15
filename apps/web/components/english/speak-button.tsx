"use client";
import { Snail, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  RATES,
  canSpeak,
  pickVoice,
  speakable,
  type Pace,
} from "@/lib/english/speech";
import { vi } from "@/messages/vi";

const t = vi.english.speech;

/**
 * Speaks English text with the browser's voice (specs/speech, S1). Renders nothing until a suitable
 * voice is found, so it never promises sound it cannot give. `private` text (from the learner's own
 * work) only uses on-device voices.
 */
export function SpeakButton({
  text,
  private: isPrivate = false,
}: {
  text: string;
  private?: boolean;
}) {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const words = speakable(text);

  useEffect(() => {
    if (!words || !canSpeak(window)) return;
    const synth = window.speechSynthesis;
    const choose = () => {
      const best = pickVoice(synth.getVoices(), !isPrivate);
      setVoice((best as SpeechSynthesisVoice | null) ?? null);
    };
    choose();
    synth.addEventListener("voiceschanged", choose);
    return () => synth.removeEventListener("voiceschanged", choose);
  }, [words, isPrivate]);

  if (!words || !voice) return null;

  const say = (pace: Pace) => {
    const synth = window.speechSynthesis;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(words);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = RATES[pace];
    synth.speak(u);
  };

  return (
    <span className="nt-speak" title={t.machineVoice}>
      <button
        type="button"
        aria-label={`${t.listen}: ${words}`}
        onClick={() => say("normal")}
      >
        <Volume2 aria-hidden size={18} />
      </button>
      <button
        type="button"
        aria-label={`${t.listenSlow}: ${words}`}
        onClick={() => say("slow")}
      >
        <Snail aria-hidden size={18} />
      </button>
    </span>
  );
}
