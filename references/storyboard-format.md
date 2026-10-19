# storyboard.json

Eén bestand per video. Volledig voorbeeld: `templates/storyboard.example.json`.

## Bovenkant

| veld | betekenis |
|---|---|
| `slug` | bestandsnaam van de eindvideo (`out/<slug>.mp4`) |
| `format` | `9:16` (standaard), `16:9`, `1:1`, `4:5` |
| `voice` | `{"mode": "tts", "file": "audio/vo.mp3"}` of `{"mode": "video", "file": "assets/talk_cut.mp4"}` (talking head; de audio komt dan uit de video) |
| `script` | de stemtekst (voor jezelf en de gebruiker; de motor gebruikt `audio/words.json`) |
| `caption_fix` | Whisper-schrijffouten voor de ondertitels: `{"zeintje": "seintje"}` |
| `caption_keywords` | woorden die de oranje markering krijgen; cijfers krijgen hem altijd |
| `caption_y` | optioneel, 0..1 van de hoogte (standaard uit defaults.json per formaat) |
| `establishing` | `true` = video begint met een wijd shot van de kamer (aanrader) |
| `music`, `music_db` | optioneel achtergrondmuziek (bestand in assets/), standaard -22 dB met ducking |
| `lead_in`, `tail` | stilte voor en na de stem (standaard 0,5 en 1,2 s) |

## Beats

Een beat = een stuk tekst op één station. Volgorde = volgorde in de video.

```json
{"station": "monitor", "from": "Elke dag", "zoom": {"box": [250, 90, 1330, 850]}, "scene": {...}}
```

- `station`: `board`, `monitor`, `phone`, `table`, `face` (talking head vol beeld).
- `from`: anker waar de beat begint. Een woord of woordgroep uit de stem ("Elke dag"), `"woord#2"` voor de tweede
  keer, of een getal in seconden vanaf het begin van de stem. Hoofdletters, leestekens en cijfers vs. woorden
  ("12" = "twaalf") maken niet uit; kleine Whisper-schrijfverschillen ook niet.
- `split: true` (alleen met een talking head): bovenste helft 3D, onderste helft het gezicht.
- `zoom`: alleen voor `monitor`: `"full"` of `{"box": [x0, y0, x1, y1]}` in pixels van het monitorbeeld (1600x900).
  De camera past de box in beeld. Monitorindeling: menubalk 0-70, zijbalk 0-230, inhoud vanaf x=264, y=96.
- `zooms`: meerdere zooms binnen één beat: `[{"zoom": {...}}, {"at": "woord", "zoom": {...}}]`.
  Gebruik dit als een beat langer dan 8 s is.

## Per station

**board**: `"lines": [{"text": "Gratis proef", "at": "gratis", "color": "brand", "size": 105, "indent": 110}]`
- `at`: het potlood begint bij dit woord (anders direct na de vorige regel). `color`: `ink` (standaard), `accent`, `brand`.
- Lettergrootte past zichzelf aan de breedte aan (max 150 px). Maximaal ca. 6 regels; houd regels kort (2-3 woorden).
- Twee board-beats = twee borden; het wisselt als de camera weg is.

**monitor**: `"scene": {"type": ..., "title", "subtitle", "nav": index in brand.app.nav, "path": "/url-pad"}`
- zie scene-library.md voor `image`, `list`, `mail`, `stat`, `bullets`, `video`.

**phone**: `"scene": {"type": "notify_chat" | "image", ...}` (zie scene-library.md).

**table**: `"plaque": {"big": "42%", "line1": "...", "line2": "..."}` of `{"image": "assets/logo.png"}`,
`"pawns": {"count": 10, "highlight": 3, "at": "drie"}` (optioneel). De robotarm zet het bordje neer.
Meerdere table-beats = meerdere bordjes na elkaar. `"clutter": {...}` = rommelige stapel facturen (zie scene-library.md);
`"zoom": {"w": 0.85}` = bredere tafelshot.

## Ankers voor momenten binnen een scène

| scène | anker | standaard |
|---|---|---|
| list | `rows_from` | 0,4 s na begin beat |
| mail | `send_at`, `tag_at` | 72% van de beat; tag 0,4 s voor versturen |
| notify_chat | `notify_at`, `open_at` | begin + 0,3 s; 55% van de beat |
| bullets | `at: ["woord", ...]` per item | elke 0,6 s |
| pawns | `at` | 0,6 s na neerzetten |
