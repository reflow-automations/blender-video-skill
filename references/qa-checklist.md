# Controlelijst

Loop dit af op het contactblad van de stills (stap 7) én op de eindvideo (stap 9). Kijk zoals een kijker op een
telefoon: is het in één seconde duidelijk? Niet: is de techniek gelukt.

## Beeld
- [ ] Niets afgesneden: tekst op schermen, pionnen, bordje, whiteboardregels vallen binnen beeld.
- [ ] Ondertitel valt niet over het onderwerp (tekst op een scherm, pionnen, bordje).
- [ ] Geen lichtvlek of glans die tekst onleesbaar maakt (whiteboard, telefoon, monitor).
- [ ] Schermen zien er echt uit: geen grijze waas, geen rare hoeken, ronde hoeken bij de telefoon.
- [ ] Elk shot toont wat er op dat moment gezegd wordt (één idee per shot).
- [ ] Niets staat langer dan 8 s stil (timeline.py waarschuwt).
- [ ] Geen zwart of leeg frame (qa.py final).
- [ ] Aan het begin weet de kijker waar hij is (wijd shot), daarna steeds: uitzoomen, bewegen, inzoomen.
- [ ] Het laatste beeld staat lang genoeg (URL of CTA af en leesbaar, minstens 0,7 s rust).

## Tekst en feiten
- [ ] Cijfers en claims komen uit bronnen van de gebruiker, met dezelfde afbakening.
- [ ] Geen echte klantnamen of klantgegevens in beeld.
- [ ] Ondertitels kloppen met wat er gezegd wordt (caption_fix voor Whisper-fouten), geen mojibake.
- [ ] Geen em- of en-dashes, geen AI-tells.

## Geluid
- [ ] Stem verstaanbaar, effecten zacht (whoosh, potlood, robot). Loudness rond -15 tot -16 LUFS.
- [ ] Stem terug naar tekst (qa.md) komt overeen met het script.

## Opleveren
- [ ] 1080 breed of hoog, yuv420p, 30 fps, faststart.
