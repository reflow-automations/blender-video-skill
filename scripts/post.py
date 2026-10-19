"""Eindmontage: ondertitels, vignet, talking head, geluidseffecten, stem, muziek -> mp4.

Gebruik: py post.py <videomap> [--preview] [--no-sfx] [--name bestandsnaam]
Leest build/timeline.json, build/render(_preview)/f_####.png, storyboard.json, brand.json.
Schrijft out/<name>.mp4 (standaard de slug uit storyboard.json; preview: out/preview.mp4).
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
D = json.loads((SKILL / "defaults.json").read_text(encoding="utf-8"))
VDIR = Path(sys.argv[1]).resolve()
PREVIEW = "--preview" in sys.argv
NOSFX = "--no-sfx" in sys.argv
TL = json.loads((VDIR / "build" / "timeline.json").read_text(encoding="utf-8"))
SB = json.loads((VDIR / "storyboard.json").read_text(encoding="utf-8"))
BR = json.loads((VDIR / "brand.json").read_text(encoding="utf-8"))
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else ("preview" if PREVIEW else SB.get("slug", "video"))
SRC = VDIR / "build" / ("render_preview" if PREVIEW else "render")
TMP = VDIR / "build" / ("comp_preview" if PREVIEW else "comp")
OUT = VDIR / "out"
TMP.mkdir(parents=True, exist_ok=True)
OUT.mkdir(exist_ok=True)
FPS, TOTAL, LEAD = TL["fps"], TL["total_frames"], TL["lead_in"]
SR = 48000
W, H = (TL["width"] // 2, TL["height"] // 2) if PREVIEW else (TL["width"], TL["height"])
sc = W / 1080 if W <= H else H / 1080
CAPD = D["captions"]
VOICE = SB.get("voice", {})

# ------------------------------------------------------------------ captions
fix = SB.get("caption_fix", {})
keyset = {k.lower() for k in SB.get("caption_keywords", [])}
words = []
for x in TL["words"]:  # Whisper splitst "e-mail" in "e" + "-mail": weer aan elkaar
    if words and x["w"].startswith("-"):
        words[-1]["w"] += x["w"]
        words[-1]["e"] = x["e"]
    else:
        words.append(dict(x))
for w in words:
    core = w["w"].strip(".,?!")
    if core in fix:
        w["w"] = w["w"].replace(core, fix[core])
chunks, cur = [], []
for w in words:
    cur.append(w)
    if w["w"][-1:] in ".,?!" or len(cur) >= CAPD["max_words"] or sum(len(x["w"]) for x in cur) > CAPD["max_chars"]:
        chunks.append(cur)
        cur = []
if cur:
    chunks.append(cur)
caps = []
for i, c in enumerate(chunks):
    s = c[0]["s"]
    e = min(chunks[i + 1][0]["s"] if i + 1 < len(chunks) else c[-1]["e"] + 0.4, c[-1]["e"] + 0.45)
    toks = [x["w"].strip(".,!").upper() for x in c]
    keys = [k for k, x in enumerate(c) if x["w"].strip(".,?!").lower() in keyset or x["w"].strip(".,?!%").isdigit()]
    hi = keys[0] if keys else max(range(len(c)), key=lambda k: len(c[k]["w"]))
    caps.append((s, e, toks, hi))

font = ImageFont.truetype(str(SKILL / "assets" / "fonts" / "montserrat.ttf"), int(CAPD["font_px_1080w"] * sc))
font.set_variation_by_name("ExtraBold")
fmt = TL["format"]
cap_y = SB.get("caption_y") or (CAPD["y_9x16"] if fmt in ("9:16", "4:5") else CAPD["y_16x9"] if fmt == "16:9" else CAPD["y_1x1"])
CAP_Y = int(H * cap_y)
hl = (BR.get("captions") or {}).get("highlight") or CAPD["highlight"]
HL = tuple(int(hl.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def caption_layer(toks, hi, pop, CAP_Y=CAP_Y):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    gap = int(18 * sc)
    widths = [d.textbbox((0, 0), t, font=font)[2] for t in toks]
    total = sum(widths) + gap * (len(toks) - 1)
    f2 = font
    if total > W * 0.9:  # te breed: kleiner
        f2 = ImageFont.truetype(str(SKILL / "assets" / "fonts" / "montserrat.ttf"), int(CAPD["font_px_1080w"] * sc * W * 0.9 / total))
        f2.set_variation_by_name("ExtraBold")
        widths = [d.textbbox((0, 0), t, font=f2)[2] for t in toks]
        total = sum(widths) + gap * (len(toks) - 1)
    x = (W - total) // 2
    asc = f2.getbbox("ÁG")
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, t in enumerate(toks):
        if i == hi:
            pad = int(12 * sc)
            d.rounded_rectangle((x - pad, CAP_Y - pad + asc[1], x + widths[i] + pad, CAP_Y + asc[3] + pad), radius=int(10 * sc), fill=HL + (255,))
            d.text((x, CAP_Y), t, font=f2, fill=(17, 17, 17, 255))
        else:
            sd.text((x, CAP_Y + int(4 * sc)), t, font=f2, fill=(0, 0, 0, 200))
            d.text((x, CAP_Y), t, font=f2, fill=(255, 255, 255, 255), stroke_width=max(1, int(2 * sc)), stroke_fill=(0, 0, 0, 255))
        x += widths[i] + gap
    out = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6 * sc)), layer)
    if pop < 1:
        s = 0.86 + 0.14 * pop
        cx, cy = W / 2, CAP_Y + (asc[3] - asc[1]) / 2
        out = out.transform(out.size, Image.AFFINE, (1 / s, 0, cx - cx / s, 0, 1 / s, cy - cy / s), resample=Image.BICUBIC)
    return out


# ------------------------------------------------------------------ talking head
face_beats = [b for b in TL["beats"] if b["station"] == "face" or b.get("split")]
FACE = None
if face_beats and VOICE.get("mode") == "video":
    FACE = VDIR / "build" / ("face_preview" if PREVIEW else "face")
    if not FACE.exists() or len(list(FACE.glob("*.jpg"))) < TOTAL - 5:
        FACE.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(VDIR / VOICE["file"]), "-vf",
                        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-q:v", "3",
                        str(FACE / "%04d.jpg")], check=True)


def face_frame(f):
    # stem begint na LEAD seconden; het gezicht dus ook
    k = f - int(LEAD * FPS)
    p = FACE / f"{max(1, k):04d}.jpg"
    return Image.open(p).convert("RGB") if p.exists() else None


def beat_at(t):
    cur = None
    for b in TL["beats"]:
        if t >= b["start"]:
            cur = b
    return cur


yy, xx = np.mgrid[0:H, 0:W]
rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
vig = np.clip(1 - 0.28 * np.clip(rr - 0.55, 0, None) ** 1.6, 0, 1)[..., None]
cache = {}
for f in range(1, TOTAL + 1):
    t = (f - 1) / FPS
    im = Image.open(SRC / f"f_{f:04d}.png").convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    b = beat_at(t)
    if FACE and b is not None and (b["station"] == "face" or b.get("split")):
        fc = face_frame(f)
        if fc is not None:
            if b["station"] == "face":
                im = fc
            else:  # boven 3D, onder gezicht
                top = im.crop((0, H // 4, W, H // 4 + H // 2))
                bot = fc.crop((0, H // 4, W, H // 4 + H // 2))
                im = Image.new("RGB", (W, H))
                im.paste(top, (0, 0))
                im.paste(bot, (0, H // 2))
    arr = (np.asarray(im).astype(np.float32) * vig).astype(np.uint8)
    im = Image.fromarray(arr).convert("RGBA")
    for (s, e, toks, hi) in caps:
        if s <= t < e:
            pop = min(1.0, (t - s) / 0.12)
            split = b is not None and b.get("split") and FACE is not None
            k = (s, round(pop, 2), split)
            if k not in cache:
                cache[k] = caption_layer(toks, hi, pop, int(H * 0.47) if split else CAP_Y)
            im = Image.alpha_composite(im, cache[k])
            break
    im.convert("RGB").save(TMP / f"c_{f:04d}.png", compress_level=1)
print("frames klaar,", len(caps), "ondertitelblokken")

# ------------------------------------------------------------------ geluidseffecten
N = int(SR * TOTAL / FPS)
sfx = np.zeros(N, np.float32)
rng = np.random.default_rng(3)
A = D["audio"]


def add(sig, t0, gain):
    i = int(t0 * SR)
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(N, i + len(sig))
    if i < N:
        sfx[i:j] += sig[: j - i] * gain


def norm(s):
    return (s / (np.abs(s).max() + 1e-9)).astype(np.float32)


def whoosh(dur):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    y1 = y2 = 0.0
    for k in range(n):
        fc = 300 + 2200 * math.sin(math.pi * k / n) ** 1.5
        w0 = 2 * math.pi * fc / SR
        a1, a2 = -2 * 0.92 * math.cos(w0), 0.92 * 0.92
        y = x[k] * 0.08 - a1 * y1 - a2 * y2
        y2, y1 = y1, y
        out[k] = y
    return norm(out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2)


def tone(freqs, dur, decay):
    t = np.arange(int(dur * SR)) / SR
    return norm(sum(np.sin(2 * np.pi * f * t) * np.exp(-t * decay) for f in freqs))


def click():
    t = np.arange(int(0.05 * SR)) / SR
    return norm(rng.standard_normal(len(t)) * np.exp(-t * 180) + np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120))


def servo(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = 140 + 60 * np.sin(np.pi * t / dur)
    s = np.sin(2 * np.pi * np.cumsum(f0) / SR) + 0.35 * np.sin(4 * np.pi * np.cumsum(f0) / SR) + 0.15 * rng.standard_normal(n)
    return norm(s * np.minimum(1, np.minimum(t / 0.08, (dur - t) / 0.12)))


if not NOSFX:
    shots = TL["shots"]
    if TL.get("establishing", True):
        add(whoosh(D["camera"]["establishing_s"] + 0.25), -0.1, A["whoosh_gain"])
    for k in range(1, len(shots)):
        same = shots[k]["station"] == shots[k - 1]["station"]
        mv = D["camera"]["zoom_move_s" if same else "move_s"]
        add(whoosh(mv + 0.25), shots[k]["start"] - mv / 2 - 0.1, A["whoosh_gain"] * (0.5 if same else 1))
    penf = VDIR / "build" / "frames" / "board_pen.json"
    if penf.exists():
        pens = json.loads(penf.read_text(encoding="utf-8"))
        for f in range(1, TOTAL + 1):
            if (pens.get(str(f)) or {}).get("writing"):
                x = np.diff(np.concatenate([[0], rng.standard_normal(SR // FPS)]))
                add((x * (0.6 + 0.4 * np.sin(np.linspace(0, 6 * np.pi, len(x))))).astype(np.float32), (f - 1) / FPS, A["pen_gain"])
    for b in TL["beats"]:
        ev, st, ty = b.get("events", {}), b["station"], (b.get("scene") or {}).get("type")
        if st == "monitor" and ty == "mail":
            add(click(), ev["send"], 0.25)
        if st == "monitor" and ty == "bullets":
            for t in ev["items"]:
                add(tone([660, 990], 0.15, 30), t, 0.12)
        if st == "phone" and "notify" in ev:
            add(tone([1318.5, 1975.5], 0.9, 6), ev["notify"], 0.22)
            add(click(), ev["open"], 0.18)
        if st == "table" and "down0" in ev:
            add(servo(ev["down1"] - ev["down0"]), ev["down0"], 0.07)
            add(tone([180], 0.12, 40), ev["down1"], 0.3)
            add(servo(ev["up1"] - ev["up0"]), ev["up0"], 0.06)
            for t in ev.get("highlight", []):
                add(tone([700, 1100], 0.12, 35), t, 0.18)
sw = VDIR / "build" / "sfx.wav"
with wave.open(str(sw), "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

# ------------------------------------------------------------------ encode
voice_src = VDIR / (VOICE.get("file") or "audio/vo.mp3")
ms = int(LEAD * 1000)
inputs = ["-framerate", str(FPS), "-i", str(TMP / "c_%04d.png"), "-i", str(voice_src), "-i", str(sw)]
fc = f"[1:a]adelay={ms}|{ms},aresample={SR}[v];[2:a]aresample={SR}[s];"
music = SB.get("music")
if music:
    inputs += ["-stream_loop", "-1", "-i", str(VDIR / music)]
    db = SB.get("music_db", A["music_db"])
    fc += (f"[3:a]aresample={SR},volume={db}dB,afade=t=out:st={TOTAL / FPS - 1.5}:d=1.5[m0];[v]asplit[v1][v2];"
           "[m0][v2]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[m];"
           "[v1][s][m]amix=inputs=3:duration=first:normalize=0,apad,")
else:
    fc += "[v][s]amix=inputs=2:duration=first:normalize=0,apad,"
fc += f"loudnorm=I={A['lufs']}:TP=-1.5:LRA=11[a]"
out = OUT / f"{NAME}.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-t", str(TOTAL / FPS),
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
print("klaar:", out)
