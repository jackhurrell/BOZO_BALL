# Optional assets

The app runs fine with none of these — they're purely for polish.

## audio/
HTML5 audio cues. Drop in any of (first match wins):
- `background.mp3` / `.m4a` / `.wav` — looping background music
- `splash.mp3` / `.m4a` / `.wav` — splash-screen sting
- `bozo.mp3` / `.m4a` / `flash.mp3` — the BOZO flash / reveal effect

Missing files are ignored silently.

## hdri/
Optional `.hdr` environment map for reflections. If absent, the scene uses a
built-in procedural `RoomEnvironment` (no external file needed), so glossy
balls still reflect a plausible room out of the box.

## models/
Optional Draco-compressed `.glb` pool table / room model. If absent, the
scene builds a table from primitives (felt bed, wooden rails, pockets).
