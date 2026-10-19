"""Woordtijden uit een stem of talking-head-video, en optioneel stiltes/versprekingen eruit knippen.

Gebruik:
  py transcribe.py <videomap> <bron.mp3|mp4> [--lang nl] [--model small]
      -> <videomap>/audio/words.json (+ audio/transcript.txt)
  py transcribe.py <videomap> <bron.mp4> --cut [--pause 0.45] [--cuts cuts.json]
      -> knipt pauzes langer dan --pause weg (en de bereiken uit cuts.json: [[start, eind], ...] in seconden
         van de bron), schrijft assets/talk_cut.mp4 en transcribeert die opnieuw.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def words_of(src, lang, model):
    from faster_whisper import WhisperModel
    tmp = Path(src).with_suffix(".16k.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(tmp)], check=True)
    w = wave.open(str(tmp))
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    w.close()
    tmp.unlink()
    m = WhisperModel(model, device="cpu", compute_type="int8")  # GPU mist cublas op deze pc
    segs, _ = m.transcribe(a, language=lang, word_timestamps=True)
    out, lines = [], []
    for s in segs:
        lines.append(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text.strip()}")
        out += [dict(w=x.word.strip(), s=round(x.start, 3), e=round(x.end, 3)) for x in s.words]
    return out, lines


def main():
    vdir, src = Path(sys.argv[1]), Path(sys.argv[2])
    if not src.is_absolute():
        src = vdir / src
    lang, model = arg("--lang", "nl"), arg("--model", "small")
    (vdir / "audio").mkdir(parents=True, exist_ok=True)
    if "--cut" in sys.argv:
        words, _ = words_of(src, lang, model)
        pause = float(arg("--pause", "0.45"))
        bad = json.loads(Path(arg("--cuts", vdir / "cuts.json")).read_text(encoding="utf-8")) if Path(arg("--cuts", vdir / "cuts.json")).exists() else []
        keep, s0 = [], max(0, words[0]["s"] - 0.15)
        for a, b in zip(words, words[1:]):
            if b["s"] - a["e"] > pause:
                keep.append([s0, a["e"] + 0.12])
                s0 = b["s"] - 0.12
        keep.append([s0, words[-1]["e"] + 0.25])
        for (x0, x1) in bad:  # versprekingen: uit de te houden stukken halen
            nk = []
            for (k0, k1) in keep:
                if x1 <= k0 or x0 >= k1:
                    nk.append([k0, k1])
                else:
                    if x0 > k0:
                        nk.append([k0, x0])
                    if x1 < k1:
                        nk.append([x1, k1])
            keep = nk
        sel = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in keep)
        dst = vdir / "assets" / "talk_cut.mp4"
        dst.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", f"select='{sel}',setpts=N/FRAME_RATE/TB",
                        "-af", f"aselect='{sel}',asetpts=N/SR/TB", "-c:v", "libx264", "-crf", "16", "-c:a", "aac", "-b:a", "192k", str(dst)], check=True)
        cut_total = sum(b - a for a, b in keep)
        print(f"geknipt: {len(keep)} stukken, {cut_total:.1f} s over -> {dst}")
        src = dst
    words, lines = words_of(src, lang, model)
    (vdir / "audio" / "words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    (vdir / "audio" / "transcript.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"{len(words)} woorden -> audio/words.json")


if __name__ == "__main__":
    main()
