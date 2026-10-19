"""Zet een nieuwe videomap klaar.

Gebruik: py new_video.py <videomap> --brand <merkprofiel> [--format 9:16] [--example] [--refresh-brand]
  <merkprofiel>: naam uit templates/brands/ (bijv. voorbeeld) of pad naar een eigen json.
  --example: zet het voorbeelddraaiboek (fictieve app Afspraakje) neer in plaats van een leeg draaiboek.
Maakt: storyboard.json, brand.json, assets/brand/*, audio/, NOTES.md
"""
import json
import shutil
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


vdir = Path(sys.argv[1]).resolve()
brand_name = arg("--brand", "voorbeeld")
bp = Path(brand_name) if brand_name.endswith(".json") else SKILL / "templates" / "brands" / f"{brand_name}.json"
brand = json.loads(bp.read_text(encoding="utf-8"))
REFRESH = "--refresh-brand" in sys.argv  # alleen merk vervangen, draaiboek laten staan
if (vdir / "storyboard.json").exists() and not REFRESH:
    sys.exit(f"{vdir} heeft al een storyboard.json; niets overschreven (merk wisselen: --refresh-brand)")
if REFRESH and (vdir / "assets" / "brand").exists():
    shutil.rmtree(vdir / "assets" / "brand")
(vdir / "assets" / "brand").mkdir(parents=True, exist_ok=True)
(vdir / "audio").mkdir(exist_ok=True)
for key, src in (brand.pop("files", {}) or {}).items():
    s = Path(src)
    if not s.is_absolute():
        s = bp.parent / s
    if s.exists():
        dst = vdir / "assets" / "brand" / f"{key}{s.suffix}"
        shutil.copyfile(s, dst)
        brand[key] = f"assets/brand/{dst.name}"
    else:
        print(f"LET OP: merkbestand ontbreekt: {src}")
brand.pop("_uitleg", None)
(vdir / "brand.json").write_text(json.dumps(brand, ensure_ascii=False, indent=1), encoding="utf-8")
if REFRESH:
    print("merk vervangen:", brand.get("name"))
    sys.exit(0)
if "--example" in sys.argv:
    sb = json.loads((SKILL / "templates" / "storyboard.example.json").read_text(encoding="utf-8"))
else:
    sb = {"slug": vdir.name, "title": "", "format": arg("--format", "9:16"), "voice": {"mode": "tts", "file": "audio/vo.mp3"},
          "script": "", "caption_fix": {}, "caption_keywords": [], "establishing": True, "beats": []}
sb["format"] = arg("--format", sb.get("format", "9:16"))
(vdir / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding="utf-8")
(vdir / "NOTES.md").write_text(f"# {vdir.name}\n\nGestart {date.today()} met skill blender-video. Merk: {brand.get('name')}.\n\n## Feedback\n\n## Wat ging mis / leerde ik\n", encoding="utf-8")
print("klaar:", vdir)
