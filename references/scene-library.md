# Scènebibliotheek

Welk beeld bij welke zin. Eén idee per shot. Wat je zegt, laat je zien.

## Stations

| station | goed voor | niet voor |
|---|---|---|
| whiteboard | hook, het probleem, de kern in 2 tot 4 woorden, CTA en URL | lange zinnen, cijfers met uitleg |
| monitor | het product zelf, lijsten, een mail of document, een getal dat optelt, stappen | iets dat op een telefoon gebeurt |
| telefoon | meldingen, een reactie, een afspraak, "je krijgt een seintje" | dashboards |
| tafel | één hard resultaat (bordje), "x op de y" (pionnen), een logo of keurmerk | uitleg |
| face (talking head) | persoonlijke opening, geloofwaardigheid, afsluiter | lange stukken zonder beeldwissel |

## Monitor-scènes (`scene.type`)

- **image**: `src` (screenshot in assets/), `title`, `subtitle`. Langzame zoom van 4%. Gebruik een echte screenshot
  van het product (Playwright), met nep-gegevens.
  `bare: true`: de screenshot vult het hele browservenster (voor echte app-schermen met eigen menu). Snijd hem op
  1440x747 (verhouding van het venster) en gebruik zoom-boxen: monitorpixel = (x * 1,111, 70 + y * 1,111).
- **list**: `columns` (2 tot 3), `rows` (max ca. 12), `status`, `counter` (true/false), `widths` (optioneel, fr per kolom),
  `rows_from` (anker). Rijen schuiven één voor één in, teller loopt mee.
- **mail**: `from`, `from_tag`, `to`, `subject`, `body` (wordt getypt), `send_at`, `tag_at`, `sent_label`,
  `note` (lijst van [kop, tekst] rechts naast de mail). Gebruik een zoom-box rond de mail (x 250 tot 1180).
- **stat**: `value` ("42%", "€ 1.200", "3 uur"), `label`, `sub`. Getal telt op.
- **bullets**: `items` (max 5, kort), `at` (ankers per item). Voor stappen of voordelen.
- **video**: `src` (mp4 in assets/), `offset`, `labels` ([[seconden, "label"], ...]). Voor "AI analyseert een video":
  stockclip met labels per scène (Riley-idee).

## Telefoon-scènes

- **notify_chat**: `app`, `title`, `message` (in de melding), `contact`, `contact_sub`, `takeover`, `reply`,
  `notify_at`, `open_at`. Lockscreen, melding, chat opent, antwoord wordt getypt en verstuurd.
  Bericht van een persoon (klant, boekhouder) in plaats van de app: `"app": "Berichten", "avatar": "M", "avatar_color": "#25a35a"`
  (of `icon` met een eigen afbeelding).
- **image**: `src` (schermafbeelding 590x1280 of groter, zelfde verhouding).

## Tafel

- **plaque** (robotarm zet het neer): `big` (max ca. 5 tekens op 230 px, bijv. "42%", "Q4"), `line1`, `line2`, of `image`.
- **pawns**: `count`, `highlight`, `at` (alleen samen met een plaque).
- **clutter** (probleem-shot, geen robotarm): `{"papers": 16, "envelopes": 6, "shoebox": true, "suppliers": [...], "client": "..."}`.
  Rommelige stapel A4-facturen (nep, "Fictief voorbeeld"), enveloppen en een schoenendoos met bonnetjes. Gebruik
  `"zoom": {"w": 0.85}` zodat alles in beeld valt. Daarna een table-beat met plaque = opgeruimde tafel (voor/na).

## Een nieuw soort scène toevoegen

1. Bedenk hem algemeen (welke velden heeft elke toekomstige video nodig?), niet voor één video.
2. Bouw hem in `scripts/screens.html` (`build` + `render`), tijden in `scripts/timeline.py` (events), geluid in
   `scripts/post.py`.
3. Documenteer hem hier en in storyboard-format.md, met een voorbeeld.
4. Test met het voorbeelddraaiboek dat de oude scènes nog werken.

## Ideeën die nog niet gebouwd zijn (bouwen zodra een video ze nodig heeft)

- Tafel: robotarm zet meerdere logo's naast elkaar (merken, tools), stopwatch, blokken uren (Riley); robotarm ruimt de rommel op.
- Monitor: Claude Code / terminal die typt, tijdlijn van een video-editor, vergelijking voor/na.
- Telefoon: WhatsApp-stijl gesprek met meerdere berichten, agenda-uitnodiging.
- Kamer: andere wandstijlen (`room.wall`: walnut, oak, dark bestaan al), klantlogo op de muur.
