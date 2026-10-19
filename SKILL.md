---
name: blender-video
description: >-
  Maakt een korte promo- of uitlegvideo in een fotorealistische 3D-kamer in Blender (stijl Riley Brown):
  camera vliegt tussen whiteboard (potlood schrijft mee), computer (app-scherm), telefoon (melding en chat)
  en tafel (robotarm zet een bordje met een cijfer neer), met stem (AI-stem of eigen opname, ook met talking
  head), gele ondertitels en geluidseffecten. Werkt voor elk product of elke dienst via een draaiboek
  (storyboard.json) en een merkprofiel; staand, liggend of vierkant. Lokaal gerenderd met EEVEE.
  Verbetert zichzelf na elke video. Trigger bij "/blender-video", "blender video", "3D-video", "video in de
  3D-kamer", "video zoals Riley", "promovideo in Blender", "uitlegvideo met whiteboard en robotarm".
  Niet voor het bewerken van bestaande video's zonder 3D-kamer.
---

# Blender-video (3D-kamer)

Eén vaste kamer, vier stations, elke video een nieuw draaiboek. De motor staat in `scripts/`; per video schrijf je
alleen `storyboard.json` (wat er wanneer te zien is) en kies je een merkprofiel.

## Eerst lezen, elke run

1. [references/lessons.md](references/lessons.md): lessen van eerdere video's. Ze gaan voor op de rest.
2. [defaults.json](defaults.json): getallen van de motor (camera, tempo, ondertitels, geluid).
3. De laatste drie regels van [references/runs.md](references/runs.md): wat de gebruiker van eerdere video's vond.
4. Wat de gebruiker over het product heeft gedeeld (website, notities): feiten, cijfers, wat wel en niet beloofd mag worden.

## Vaste regels

- **Geen verzonnen feiten.** Cijfers, resultaten en claims alleen uit bronnen van de gebruiker, met dezelfde
  afbakening (bijv. "resultaat bij één klant"). Voorbeeldnamen van bedrijven en personen mogen, maar zijn fictief
  en nooit van echte klanten.
- **Klantdata nooit in beeld** zonder akkoord van de gebruiker. Echte schermen: eerst nep-gegevens of blur.
- **Gesproken taal:** kort, één gedachte per zin. Getallen voluit schrijven in de stemtekst ("twaalf"), cijfers op
  het scherm.
- **Copy eerst bespreken** bij een nieuwe advertentie of een nieuwe hook: twee richtingen voorleggen, tenzij de
  gebruiker zegt "ga door". Renderen is gratis (lokaal); een AI-stem kost meestal een paar cent.
- **Encoding:** alle bestanden UTF-8 zonder BOM; na schrijven terugscannen op kapotte tekens (`Ã`, `ðŸ`).
- **Nooit een betaalde cloud-GPU** zonder akkoord. Lokaal is het ca. 1 s per frame op een gewone gamekaart.
- **Paden:** altijd absolute paden. Blender: `blender` op het PATH, of vraag de gebruiker eenmalig het pad naar
  `blender.exe` en noteer het in `references/lessons.md`.

## Waar de video komt

- Vraag de gebruiker naar een map, of gebruik `<werkmap>/videos/<YYYY-MM-DD>-<slug>/`.
- `build/` en `out/` niet in git.

## Werkwijze

Scripts staan in de map `scripts/` van deze skill (hieronder `$S`). Videomap = `$V`.

1. **Intake (kort).** Wat verkoop je, aan wie, waar komt de video (ad, organisch, landingspagina), formaat
   (9:16 standaard; 16:9 voor YouTube/website; 1:1 of 4:5 voor feed), lengte (20 tot 45 s), stem (AI of eigen
   opname), CTA. Kies stations per zin met [references/scene-library.md](references/scene-library.md).
2. **Map en merk.** `python $S/new_video.py "$V" --brand <profiel> [--format 16:9]`. Profielen: `templates/brands/`.
   Nieuw merk: kopieer `voorbeeld.json`, vul logo's en kleuren in, sla het op in `templates/brands/`.
3. **Script.** Schrijf de stemtekst met per zin een opmerking welk station en wat er te zien is (zoals Riley).
   Zet hem in `storyboard.json` (`script`).
4. **Stem.**
   - AI: elke tekst-naar-spraakdienst die een mp3 oplevert (bijv. ElevenLabs). Sla op als `$V/audio/vo.mp3`.
     Noteer de gekozen stem in `defaults.json` (`voice`), zodat volgende video's dezelfde stem krijgen.
   - Eigen opname (talking head): zet de mp4 in `$V/assets/`. Knip pauzes en versprekingen:
     `python $S/transcribe.py "$V" assets/talk.mp4 --cut [--cuts cuts.json]` en zet in het draaiboek
     `"voice": {"mode": "video", "file": "assets/talk_cut.mp4"}`.
   - Woordtijden: `python $S/transcribe.py "$V" audio/vo.mp3` (bij `--cut` gebeurt dit al).
5. **Draaiboek.** Vul `beats` volgens [references/storyboard-format.md](references/storyboard-format.md). Ankers zijn
   woorden uit de stem. Echte productschermen: screenshot met Playwright naar `$V/assets/` (nep-gegevens).
   Dan `python $S/timeline.py "$V"`: los elke "LET OP" op (anker niet gevonden, shot langer dan 8 s).
6. **Schermen.** `python $S/render_screens.py "$V"` (stilstaande beelden worden gekopieerd, snel).
7. **Preview van elke shot** (zoals Riley: eerst kijken, dan pas renderen).
   `F=$(python $S/qa.py "$V" stills)` en `blender -b -P $S/room.py -- "$V" --stills "$F"`, dan
   `python $S/qa.py "$V" sheet` en het contactblad `build/qa/sheet.jpg` ZELF bekijken met
   [references/qa-checklist.md](references/qa-checklist.md). Fouten eerst oplossen.
8. **Render.** `blender -b -P $S/room.py -- "$V" --render` (achtergrond, ca. 15 tot 25 min voor 30 s). Daarna
   `python $S/post.py "$V"` (met `"music": "assets/x.mp3"` in het draaiboek komt er muziek onder, met ducking).
   Alleen een deel opnieuw: `--frames A-B`.
9. **Eindcontrole.** `python $S/qa.py "$V" final "$V/out/<slug>.mp4"`: contactblad + `build/qa/qa.md` (formaat,
   loudness, donkere frames, stem terug naar tekst). Bekijk het contactblad op volle grootte. Pas dan "klaar".
10. **Opleveren.** Geef de gebruiker het pad naar `out/<slug>.mp4` en vertel wat je nog niet hebt gecontroleerd
    (bijv. kijken op een telefoon). Daarna "Zelf verbeteren".

## Kiezen per situatie

- **Product met een app:** monitor met echte UI (screenshot of nagebouwde lijst/mail), telefoon voor meldingen.
- **Dienst zonder app (consultancy, workshop, bouwwerk):** whiteboard voor de kern, monitor met `bullets` of
  `stat`, tafel voor het resultaat. Telefoon alleen als er echt een bericht/afspraak in het verhaal zit.
- **Cijfer of resultaat:** tafel (robotarm + bordje, pionnen voor "x op de y") of monitor `stat`.
- **Hook en CTA:** whiteboard; eerste en laatste beat. URL of actie als laatste regel.
- **Klant of persoon zelf aan het woord:** talking head (`face` vol beeld voor de hook, `split: true` daarna).
- **Liggend (16:9):** zelfde draaiboek, `--format 16:9`; de camera past zich vanzelf aan. Controleer het contactblad.

## Zelf verbeteren (verplicht, elke run)

1. **Tijdens de run:** liep iets mis of vroeg de gebruiker iets aan te passen, schrijf het meteen in
   [references/lessons.md](references/lessons.md): datum, video, wat er gebeurde, de regel voortaan.
2. **Aan het eind:**
   - Een les met een getal (afstand, tempo, grootte, volume): pas [defaults.json](defaults.json) aan en noteer oud
     en nieuw in de les. Een les die alleen in `lessons.md` staat, wordt vergeten.
   - Een les over controle: zet een regel in [references/qa-checklist.md](references/qa-checklist.md).
   - Een nieuw soort scherm of shot nodig gehad: bouw het algemeen (in `screens.html`/`room.py`), documenteer het
     in `scene-library.md`, nooit als losse uitzondering voor één video.
   - Zet een regel in [references/runs.md](references/runs.md): datum, video, formaat, lengte, rendertijd,
     wat goed ging, feedback van de gebruiker (letterlijk), wat je aanpaste.
   - Werkte iets drie runs zonder problemen: maak de instructie korter.
   - Voeg een regel toe aan "Versies" en meld in één regel wat er aan de skill veranderde.
3. **Grenzen:** haal nooit een vaste regel weg zonder akkoord van de gebruiker. Houd deze SKILL.md onder 200
   regels; details horen in `references/`. Test na een motorwijziging met het voorbeeld (`new_video.py --example`).

## Versies
- 2026-10-19: deelbare versie. Eigen merkprofielen en klantvoorbeelden eruit, neutraal voorbeeld (fictieve
  kapsalon-app "Afspraakje"), stem en Blender-pad algemeen gemaakt.
- 2026-10-18: eerste versie, gebouwd uit twee echte promovideo's en de gids van Riley Brown
  (references/riley-guide.md). Motor algemeen gemaakt (draaiboek, merkprofielen, formaten, talking head,
  muziek, robotarm met meerdere bordjes, rommel op tafel).
