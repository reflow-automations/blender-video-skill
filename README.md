# blender-video, een Claude Code-skill

Maakt een korte promo- of uitlegvideo in een 3D-kamer in Blender: een camera vliegt langs een whiteboard (een potlood
schrijft mee), een computer, een telefoon en een tafel waar een robotarm een bordje met een cijfer neerzet. Met stem,
ondertitels en geluidjes. Gebaseerd op de werkwijze van Riley Brown (agentnative.inc/resources/blender-video-process).

Gedeeld door Rogier Helvensteijn (Reflow Automations). Gratis te gebruiken en aan te passen. Gebruik op eigen risico.

## Downloaden

- Makkelijkst: download `blender-video.zip` onder **Releases** (rechts op deze pagina) en pak hem uit in `~/.claude/skills/`.
- Met git: `git clone https://github.com/reflow-automations/blender-video-skill.git ~/.claude/skills/blender-video`

## Installeren

1. Zet de map `blender-video` in `~/.claude/skills/` (Windows: `C:/Users/<jij>/.claude/skills/`).
2. Installeer:
   - Blender 4.x of 5.x (getest met 5.2.2). Tip voor Windows: de draagbare zip van download.blender.org.
   - Python 3.10 of nieuwer met `pip install pillow numpy playwright faster-whisper` en daarna `playwright install chromium`.
   - ffmpeg op het PATH.
3. Start Claude Code en typ `/blender-video`, of vraag "maak een 3D-video over ...".

## Wat je zelf regelt

- Een stem: een AI-stem (bijv. ElevenLabs) of je eigen opname. De skill vraagt je ernaar.
- Je merk: kopieer `templates/brands/voorbeeld.json` en zet je eigen logo's en kleuren erin.

## Proberen zonder eigen product

Het voorbeelddraaiboek (`templates/storyboard.example.json`) gaat over een verzonnen kapsalon-app, "Afspraakje".
Alle namen en cijfers daarin zijn fictief.

## Hoe lang duurt het

Renderen gaat lokaal met EEVEE: ca. 15 tot 25 minuten voor 30 seconden video op een gewone gamekaart.

## Zelf verbeteren

De skill schrijft na elke video zijn lessen op in `references/lessons.md` en past `defaults.json` aan. Hoe vaker je
hem gebruikt, hoe beter hij aansluit op jouw smaak.

## Licenties

De lettertypen (Bricolage Grotesque, Hanken Grotesk, Caveat, Montserrat) vallen onder de SIL Open Font License 1.1.
Zie `assets/fonts/`.
