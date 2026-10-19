"""Rendert de schermtexturen per frame uit build/timeline.json.

Gebruik: py render_screens.py <videomap> [monitor phone board plaque] [--only F] [--step N]
Output: <videomap>/build/frames/<scherm>/0001.jpg ..., build/frames/board_pen.json, build/plaques/plaque_<beat>.png
Een scherm zonder beats wordt overgeslagen. Frames die gelijk blijven worden niet opnieuw gescreenshot
(alleen gekopieerd), dat scheelt veel tijd bij stilstaande beelden.
"""
import json
import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
HTML = SKILL / "scripts" / "screens.html"
SIZES = {"monitor": (1600, 900), "phone": (590, 1280), "board": (900, 1200), "plaque": (1040, 460), "paper": (707, 1000)}


def main():
    vdir = Path(sys.argv[1]).resolve()
    which = [a for a in sys.argv[2:] if a in SIZES] or list(SIZES)
    only = [int(sys.argv[sys.argv.index("--only") + 1])] if "--only" in sys.argv else None
    tl = json.loads((vdir / "build" / "timeline.json").read_text(encoding="utf-8"))
    brand = json.loads((vdir / "brand.json").read_text(encoding="utf-8"))
    total, fps = tl["total_frames"], tl["fps"]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for s in which:
            w, h = SIZES[s]
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(HTML.as_uri())
            pg.evaluate("Promise.all([document.fonts.load('700 100px Hand'), document.fonts.load('700 30px UI'), document.fonts.load('800 60px Display'), document.fonts.load('800 60px Caps')])")
            n = pg.evaluate("([tl, br, v, s]) => setup(tl, br, v, s)", [tl, brand, vdir.as_uri() + "/", s])
            if not n:
                print(s, "geen beats, overgeslagen")
                continue
            pg.wait_for_timeout(500)
            if s == "paper":
                out = vdir / "build" / "papers"
                out.mkdir(parents=True, exist_ok=True)
                for i in range(n):
                    pg.evaluate(f"render({i})")
                    pg.wait_for_timeout(120)
                    pg.screenshot(path=str(out / f"paper_{i}.png"))
                print("paper klaar", n)
                continue
            if s == "plaque":
                out = vdir / "build" / "plaques"
                out.mkdir(parents=True, exist_ok=True)
                beats = [x for x in tl["beats"] if x["station"] == "table" and x.get("plaque")]
                for i, bt in enumerate(beats):
                    pg.evaluate(f"render({i})")
                    pg.wait_for_timeout(150)
                    pg.screenshot(path=str(out / f"plaque_{bt['i']}.png"))
                print("plaque klaar", len(beats))
                continue
            out = vdir / "build" / "frames" / s
            out.mkdir(parents=True, exist_ok=True)
            pens, prev_html, prev_file = {}, None, None
            for f in only or range(1, total + 1):
                t = (f - 1) / fps
                pen = pg.evaluate(f"render({t})")
                if s == "board":
                    pens[f] = pen
                state = pg.evaluate("document.getElementById('root').innerHTML")
                dst = out / f"{f:04d}.jpg"
                has_video = pg.evaluate("!!document.querySelector('.pane[style*=\"block\"] video')")
                if state == prev_html and prev_file and not only and not has_video:
                    shutil.copyfile(prev_file, dst)
                else:
                    pg.screenshot(path=str(dst), type="jpeg", quality=92)
                prev_html, prev_file = state, dst
            if s == "board" and not only:
                (vdir / "build" / "frames" / "board_pen.json").write_text(json.dumps(pens), encoding="utf-8")
            print(s, "klaar")
        b.close()


if __name__ == "__main__":
    main()
