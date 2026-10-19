"""Controle na een render: contactblad per beat, zwarte/ontbrekende frames, stem terug naar tekst, loudness.

Gebruik:
  py qa.py <videomap> stills          -> lijst met framenummers (midden van elke beat + elke beweging) voor room.py --stills
  py qa.py <videomap> sheet [map]     -> build/qa/sheet.jpg uit build/stills (of opgegeven map met f_####.png)
  py qa.py <videomap> final <mp4>     -> build/qa/final_sheet.jpg + build/qa/qa.md (frames, LUFS, transcript)
Bekijk het contactblad ALTIJD zelf (Read) en loop references/qa-checklist.md af.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

VDIR = Path(sys.argv[1]).resolve()
MODE = sys.argv[2]
TL = json.loads((VDIR / "build" / "timeline.json").read_text(encoding="utf-8"))
QA = VDIR / "build" / "qa"
QA.mkdir(parents=True, exist_ok=True)
FPS = TL["fps"]


def key_frames():
    fr = set()
    for b in TL["beats"]:
        fr.add(int((b["start"] + b["end"]) / 2 * FPS) + 1)
        fr.add(int(min(b["end"] - 0.3, b["start"] + 1.2) * FPS) + 1)
    for s in TL["shots"]:
        fr.add(max(1, int(s["start"] * FPS) + 1))
    return sorted(f for f in fr if 1 <= f <= TL["total_frames"])


def sheet(paths, dst, labels):
    ims = [Image.open(p).convert("RGB") for p in paths]
    tw = 300 if TL["height"] >= TL["width"] else 480
    th = int(tw * TL["height"] / TL["width"])
    cols = 6 if tw == 300 else 4
    rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (tw * cols, (th + 24) * rows), (20, 20, 20))
    d = ImageDraw.Draw(s)
    for i, (im, lb) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * tw, (i // cols) * (th + 24)
        s.paste(im.resize((tw, th)), (x, y + 24))
        d.text((x + 6, y + 5), lb, fill=(255, 220, 120))
    s.save(dst, quality=88)
    print("contactblad:", dst)


if MODE == "stills":
    print(",".join(str(f) for f in key_frames()))
elif MODE == "sheet":
    src = Path(sys.argv[3]) if len(sys.argv) > 3 else VDIR / "build" / "stills"
    ps = sorted(src.glob("f_*.png"))
    sheet(ps, QA / "sheet.jpg", [f"{p.stem[2:]} / {(int(p.stem[2:]) - 1) / FPS:.1f}s" for p in ps])
elif MODE == "final":
    mp4 = Path(sys.argv[3])
    fr = key_frames()
    paths = []
    for f in fr:
        p = QA / f"k_{f:04d}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{(f - 1) / FPS:.3f}", "-i", str(mp4), "-frames:v", "1", str(p)], check=True)
        paths.append(p)
    sheet(paths, QA / "final_sheet.jpg", [f"{(f - 1) / FPS:.1f}s" for f in fr])
    dark = []
    for f, p in zip(fr, paths):
        im = Image.open(p).convert("L").resize((64, 64))
        if sum(im.getdata()) / 4096 < 8:
            dark.append(f)
        p.unlink()
    lufs = subprocess.run(["ffmpeg", "-i", str(mp4), "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = [l.strip() for l in lufs.splitlines() if l.strip().startswith("I:")][-1:]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,pix_fmt", "-show_entries", "format=duration",
                            "-of", "compact", str(mp4)], capture_output=True, text=True).stdout.strip()
    sys.argv = [sys.argv[0], str(VDIR), str(mp4)]
    from faster_whisper import WhisperModel  # noqa: E402
    import numpy as np, wave  # noqa: E401,E402
    wav = QA / "chk.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-ac", "1", "-ar", "16000", str(wav)], check=True)
    w = wave.open(str(wav))
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    w.close()
    wav.unlink()
    segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(a, language="nl")
    txt = "\n".join(f"[{s.start:5.1f}] {s.text.strip()}" for s in segs)
    rep = f"# QA {mp4.name}\n\n- ffprobe: {probe}\n- loudness: {lufs}\n- donkere frames: {dark or 'geen'}\n\n## Stem terug naar tekst\n\n{txt}\n"
    (QA / "qa.md").write_text(rep, encoding="utf-8")
    print(rep)
