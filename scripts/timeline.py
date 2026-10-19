"""Draaiboek + woordtijden -> timeline.json (alle tijden in videoseconden).

Gebruik: py timeline.py <videomap>
Leest  <videomap>/storyboard.json, <videomap>/audio/words.json, skill defaults.json
Schrijft <videomap>/build/timeline.json en print waarschuwingen (ankers niet gevonden, te lange shots).

Ankers: overal waar een tijd nodig is mag je een woord geven ("from": "twaalf") of een
getal in seconden vanaf het begin van de stem ("from": 7.4). Een woord wordt gezocht vanaf
het vorige anker, hoofdletters en leestekens tellen niet. "woord#2" = tweede keer.
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DEFAULTS = json.loads((SKILL / "defaults.json").read_text(encoding="utf-8"))
FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
NUM = {"0": "nul", "1": "een", "2": "twee", "3": "drie", "4": "vier", "5": "vijf", "6": "zes", "7": "zeven", "8": "acht",
       "9": "negen", "10": "tien", "11": "elf", "12": "twaalf", "20": "twintig", "40": "veertig", "100": "honderd"}

warnings = []


def norm(w):
    w = re.sub(r"[^\w%]", "", str(w).lower())
    return NUM.get(w, w)


def same(a, b):
    """Gelijk, of bijna gelijk (Whisper schrijft soms 'verstuurt' voor 'verstuurd')."""
    return a == b or (len(a) > 3 and len(b) > 3 and SequenceMatcher(None, a, b).ratio() >= 0.8)


def match(words, i, target):
    return all(same(norm(words[i + k]["w"]), target[k]) for k in range(len(target)))


class Anchors:
    def __init__(self, words, lead):
        self.words = words
        self.lead = lead
        self.cursor = 0

    def find(self, spec, default=None, move=True, label="", after=None):
        """Geeft videotijd van het begin van het woord (of getal in stemtijd).
        after: zoek pas vanaf deze videotijd (bijv. het begin van de beat)."""
        if spec is None:
            return default
        if isinstance(spec, (int, float)):
            return float(spec) + self.lead
        txt, nth = (spec.split("#") + ["1"])[:2]
        target = [norm(x) for x in txt.split()]
        hits = 0
        start = self.cursor
        if after is not None:
            start = next((i for i, w in enumerate(self.words) if w["s"] + self.lead >= after - 0.05), len(self.words))
        for i in range(start, len(self.words) - len(target) + 1):
            if match(self.words, i, target):
                hits += 1
                if hits == int(nth):
                    if move:
                        self.cursor = i
                    return self.words[i]["s"] + self.lead
        # tweede poging: vanaf het begin
        for i in range(0, len(self.words) - len(target) + 1):
            if match(self.words, i, target):
                warnings.append(f"anker '{spec}' ({label}) lag vóór het vorige anker; toch gebruikt")
                return self.words[i]["s"] + self.lead
        warnings.append(f"anker '{spec}' ({label}) niet gevonden in de stem")
        return default


def main(vdir):
    vdir = Path(vdir)
    sb = json.loads((vdir / "storyboard.json").read_text(encoding="utf-8"))
    words = json.loads((vdir / "audio" / "words.json").read_text(encoding="utf-8"))
    d = DEFAULTS
    lead = sb.get("lead_in", d["lead_in"])
    tail = sb.get("tail", d["tail"])
    fps = sb.get("fps", d["fps"])
    fmt = sb.get("format", "9:16")
    W, H = FORMATS[fmt]
    voice_end = words[-1]["e"] + lead
    duration = round(voice_end + tail, 2)
    total = int(round(duration * fps))
    A = Anchors(words, lead)

    beats = []
    for i, b in enumerate(sb["beats"]):
        st = A.find(b.get("from"), None, label=f"beat {i} from")
        if st is None:
            st = beats[-1]["start"] + 2.0 if beats else lead
        if i == 0:
            st = 0.0
        beats.append(dict(b, i=i, start=round(st, 3)))
    for i, b in enumerate(beats):
        b["end"] = beats[i + 1]["start"] if i + 1 < len(beats) else duration
        if b["end"] - b["start"] < 1.2:
            warnings.append(f"beat {i} ({b['station']}) duurt maar {b['end'] - b['start']:.1f} s")

    # interne momenten per scène oplossen
    A.cursor = 0
    for b in beats:
        A.find(b.get("from"), None, label="cursor")  # cursor naar het begin van deze beat
        s, e = b["start"], b["end"]
        L = e - s
        sc = b.get("scene") or {}
        st = b["station"]
        ev = {}
        if st == "board":
            lines = b.get("lines", [])
            t = s + d["board"]["first_line_delay"]
            for k, ln in enumerate(lines):
                a = A.find(ln.get("at"), None, label=f"beat {b['i']} regel {k}") if ln.get("at") else None
                t0 = max(t, a - 0.1) if a else t
                dur = max(d["board"]["min_line_s"], d["board"]["s_per_char"] * len(ln["text"]))
                last = b is beats[-1]
                ln["t0"], ln["t1"] = round(t0, 3), round(t0 + dur if last else min(t0 + dur, e - 0.2), 3)
                t = ln["t1"] + d["board"]["gap_s"]
        elif st == "monitor":
            ty = sc.get("type")
            if ty == "list":
                n = len(sc.get("rows", []))
                r0 = A.find(sc.get("rows_from"), s + 0.4, move=False, label="rows_from")
                span = min(L * 0.6, 0.2 * n + 0.3)
                ev["rows"] = [round(r0 + k * span / max(1, n), 3) for k in range(n)]
            elif ty == "mail":
                t0 = s + 0.45
                send = A.find(sc.get("send_at"), s + L * 0.72, move=False, label="send_at")
                ev["type0"], ev["type1"] = round(t0, 3), round(max(t0 + 1.0, send - 0.6), 3)
                ev["send"] = round(send, 3)
                ev["tag"] = round(A.find(sc.get("tag_at"), send - 0.4, move=False, label="tag_at"), 3)
            elif ty in ("stat",):
                ev["count0"] = round(s + 0.3, 3)
                ev["count1"] = round(s + min(1.8, L * 0.5), 3)
            elif ty == "bullets":
                n = len(sc.get("items", []))
                ats = sc.get("at", [])
                ev["items"] = [round(A.find(ats[k], s + 0.4 + k * 0.6, move=False, label=f"bullet {k}") if k < len(ats) else s + 0.4 + k * 0.6, 3) for k in range(n)]
        elif st == "phone":
            if sc.get("type", "notify_chat") == "notify_chat":
                ev["notify"] = round(A.find(sc.get("notify_at"), s + 0.3, move=False, label="notify_at"), 3)
                ev["open"] = round(A.find(sc.get("open_at"), s + L * 0.55, move=False, label="open_at"), 3)
                ev["reply0"] = round(ev["open"] + 0.25, 3)
                ev["reply1"] = round(min(e - 0.6, ev["reply0"] + 1.2), 3)
                ev["sent"] = round(ev["reply1"] + 0.1, 3)
        elif st == "table" and b.get("plaque"):
            arm = d["table"]
            ev["down0"] = round(s + arm["down_delay"], 3)
            ev["down1"] = round(ev["down0"] + arm["down_s"], 3)
            ev["release"] = round(ev["down1"] + 0.1, 3)
            ev["up0"] = round(ev["release"] + 0.2, 3)
            ev["up1"] = round(ev["up0"] + arm["up_s"], 3)
            pw = b.get("pawns")
            if pw:
                h0 = A.find(pw.get("at"), ev["release"] + 0.6, move=False, label="pawns.at")
                ev["highlight"] = [round(h0 + k * 0.12, 3) for k in range(pw.get("highlight", 0))]
        b["events"] = ev
        for k, v in ev.items():  # momenten die buiten hun eigen beat vallen
            for x in (v if isinstance(v, list) else [v]):
                if not (s - 0.05 <= x <= e + 0.05):
                    warnings.append(f"beat {b['i']} ({st}): moment '{k}' op {x:.1f} s valt buiten de beat ({s:.1f}-{e:.1f} s); kies een woord binnen de beat")

    # laatste beat: video zo lang maken dat het schrijven af is (plus rust)
    fin = beats[-1]
    if fin["station"] == "board" and fin.get("lines"):
        need = max(l["t1"] for l in fin["lines"]) + 0.7
        if need > duration:
            warnings.append(f"video verlengd van {duration:.2f} naar {need:.2f} s zodat het whiteboard af is")
            duration = round(need, 2)
            total = int(round(duration * fps))
            fin["end"] = duration

    # wisselmomenten van schermen: halverwege als de camera weg is, anders op het beatbegin
    for st in ("board", "monitor", "phone", "table"):
        prev = None
        for b in beats:
            if b["station"] != st:
                continue
            if prev is None:
                b["swap"] = 0.0
            elif prev["i"] == b["i"] - 1:
                b["swap"] = b["start"]
            else:
                b["swap"] = round((prev["end"] + b["start"]) / 2, 3)
            prev = b

    # shots voor de camera
    shots = []
    for b in beats:
        if b["station"] == "face":  # talking head vol beeld: camera hoeft niets
            continue
        zooms = b.get("zooms") or [{"at": None, "zoom": b.get("zoom", "full")}]
        for k, z in enumerate(zooms):
            zs = b["start"] if k == 0 else A.find(z.get("at"), b["start"] + 1.5 * k, move=False, label="zoom.at", after=b["start"])
            shots.append(dict(station=b["station"], zoom=z.get("zoom", "full"), start=round(zs, 3), beat=b["i"], split=bool(b.get("split"))))
    for k, sh in enumerate(shots):
        sh["end"] = shots[k + 1]["start"] if k + 1 < len(shots) else duration
        if sh["end"] - sh["start"] > 8.0:
            warnings.append(f"shot op {sh['station']} van {sh['start']:.1f} tot {sh['end']:.1f} s staat langer dan 8 s op één beeld: voeg een zoom toe")

    out = dict(fps=fps, total_frames=total, duration=duration, format=fmt, width=W, height=H, lead_in=lead,
               voice_end=round(voice_end, 3), words=[dict(w=x["w"], s=round(x["s"] + lead, 3), e=round(x["e"] + lead, 3)) for x in words],
               beats=beats, shots=shots, establishing=sb.get("establishing", True), warnings=warnings)
    (vdir / "build").mkdir(exist_ok=True)
    (vdir / "build" / "timeline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"timeline: {len(beats)} beats, {len(shots)} shots, {duration:.2f} s, {total} frames, {W}x{H}")
    for b in beats:
        print(f"  {b['start']:6.2f}-{b['end']:6.2f}  {b['station']:8s} {(b.get('scene') or {}).get('type', '')}")
    for w in warnings:
        print("  LET OP:", w)


if __name__ == "__main__":
    main(sys.argv[1])
