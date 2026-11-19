"""Voice a two-speaker dialogue with two Piper voices; write one WAV with short pauses between turns."""
import io, json, time, wave
from piper import PiperVoice, SynthesisConfig
voices = {"F": PiperVoice.load("/w/voices/en_GB-alba-medium.onnx"),
          "M": PiperVoice.load("/w/voices/en_GB-northern_english_male-medium.onnx")}
turns = json.load(open("/w/dialogue.json"))
pcm, rate, t0, spoken = bytearray(), 22050, time.time(), 0
for who, text in turns:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        voices[who].synthesize_wav(text, w, syn_config=SynthesisConfig())
    with wave.open(io.BytesIO(buf.getvalue())) as r:
        frames = r.readframes(r.getnframes()); rate = r.getframerate()
    pcm += frames + b"\x00\x00" * int(rate * 0.45)  # a short gap between turns
synth = time.time() - t0
with wave.open("/w/out/part1-sample.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(pcm))
secs = len(pcm) / 2 / rate
print(json.dumps({"turns": len(turns), "audio_seconds": round(secs, 1), "synthesis_seconds": round(synth, 1),
                  "x_real_time": round(synth / secs, 3)}))
