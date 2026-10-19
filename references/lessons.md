# Lessen

Nieuwste onderaan. Elke regel: datum, video, wat er gebeurde, de regel voortaan. Verwerkt in code of defaults? Zet er
"verwerkt in <bestand>" achter.

## Uit de eerste twee promovideo's (2026-10-18)

- 2026-10-18: `winget install BlenderFoundation.Blender` bleef hangen op de admin-vraag. Regel: draagbare zip van
  download.blender.org uitpakken in een eigen map en dat pad gebruiken.
- 2026-10-18: Blender-sensor: met `sensor_fit VERTICAL` en 24 mm is het beeld in 9:16 veel smaller dan je denkt;
  tekst viel van de rand. Regel: nooit afstanden gokken, de camera rekent met `fit()` vanuit de breedte én hoogte.
  Verwerkt in room.py.
- 2026-10-18: AgX maakte schermen grijs. Regel: view transform Standard, look Medium High Contrast, exposure -0,3.
  Verwerkt in room.py en defaults.json.
- 2026-10-18: glanzend whiteboard (roughness 0,22) gaf een lichtvlek waardoor tekst leek weg te vallen. Regel:
  roughness 0,6 en specular 0,15. Verwerkt in room.py.
- 2026-10-18: telefoon/tablet plat op tafel, van bovenaf, oogde nep (vlekkerig hout, grijze hoekjes, glans).
  Regel: telefoon rechtop op een standaard, scherm zonder specular, ronde hoeken via eigen geometrie
  (`rr_points`), niet via bmesh-bevel. Verwerkt in room.py.
- 2026-10-18: bmesh.ops.bevel op losse hoekpunten gaf rare vormen. Regel: omtrek zelf uitrekenen. Verwerkt in room.py.
- 2026-10-18: hout met distortion 9 leek op marmer van dichtbij. Regel: bureau en tafel distortion 2,5, schaal langs
  de nerf. Verwerkt in room.py.
- 2026-10-18: ondertitel viel over de pionnen op tafel. Regel: kleine onderwerpen hoger in beeld zetten
  (`subject_center_9x16` 0,42). Verwerkt in room.py (`fit`) en defaults.json.
- 2026-10-18: laatste whiteboardregel was nog niet af aan het eind. Regel: timeline.py verlengt de video tot het
  schrijven klaar is plus 0,7 s. Verwerkt in timeline.py.
- 2026-10-18: Whisper schrijft "verstuurt" voor "verstuurd", "zeintje" voor "seintje", cijfers als "12". Regel:
  ankers zoeken met bijna-gelijk en cijfer=woord; ondertitels via `caption_fix`. Verwerkt in timeline.py.
- 2026-10-18: zoom-anker in een beat zocht vanaf het einde van de video. Regel: ankers binnen een beat zoeken vanaf
  het begin van die beat (`after`). Verwerkt in timeline.py.
- 2026-10-18: elk frame van elk scherm screenshotten duurde 6 minuten. Regel: gelijk gebleven frames kopiëren.
  Nu 27 s. Verwerkt in render_screens.py.
- 2026-10-18: faster-whisper met een bestandspad faalt (PyAV te nieuw); GPU mist cublas. Regel: audio via ffmpeg
  naar 16 kHz wav en als numpy-array doorgeven, CPU int8. Verwerkt in transcribe.py en qa.py.
- 2026-10-18: preview op halve grootte verbergt fouten (lichtvlek, hoekjes, overlappende ondertitel). Regel: stills
  op volle grootte bekijken vóór de render, en de eindvideo nog een keer. Verwerkt in qa-checklist.md.

## Uit de skilltest (2026-10-18, motor algemeen gemaakt)

- 2026-10-18: lijst met 3 kolommen gaf "Waarom nu" over twee regels. Regel: eerste en laatste tekstkolom breder
  (1,6 fr), of `widths` in de scène. Verwerkt in screens.html.
- 2026-10-18: een anker in een andere beat liet een item pas na de beat verschijnen, zonder melding. Regel:
  timeline.py waarschuwt als een moment buiten zijn beat valt. Verwerkt in timeline.py.
- 2026-10-18: opsomming (32 px) was op 9:16 bijna onleesbaar. Regel: 50 px vet, max 5 items. Verwerkt in screens.html.
- 2026-10-18: tafelshot via `fit()` zette de pionnen weer onder de ondertitel. Regel: richtpunt tafel (2,0; 1,88; 0,735);
  na elke cameraswijziging de tafelshot opnieuw checken. Verwerkt in room.py.
- 2026-10-18: bij een gedeeld scherm (talking head onder) viel het whiteboard half buiten het bovenvak. Regel: voor
  split-beats kadert de camera voor een half beeld; ondertitel op 0,47 (de naad). Verwerkt in room.py en post.py.
- 2026-10-18: alle screenshots per frame: 6 min; met kopiëren van gelijke frames 27 s. Losse stills uit Blender: ca.
  0,3 s per beeld; hele video op halve grootte ca. 8 min, volle grootte ca. 20 min (34 s video, gamekaart van 2025).

## Uit de tweede video (2026-10-18)

- 2026-10-18: eerste whiteboardregel met een anker laat in de zin gaf 3 s een leeg bord. Regel: eerste regel van de
  eerste beat zonder `at` (begint meteen).
- 2026-10-18: Whisper splitst "e-mail" in "e" + "-mail". Regel: post.py plakt woorden met een voorloopstreepje vast.
  Verwerkt in post.py.
- 2026-10-18: lange app-screenshots (hele pagina) passen niet op een monitor. Regel: bovenste 1440x747 uitsnijden en
  `bare: true`; zoom-boxen op de kern (KPI-blok, tabel). Verwerkt in scene-library.md.
- 2026-10-18: een stem die de gebruiker al goedgekeurd heeft eerst hergebruiken in plaats van een nieuwe AI-stem.
- 2026-10-18: geel als accentkleur werkt niet op een wit whiteboard. Regel: op het bord `brand` gebruiken,
  geel alleen op donker (bordje, ondertitel).
