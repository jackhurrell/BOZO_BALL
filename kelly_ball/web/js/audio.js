// Cross-platform audio via HTML5 <audio>, replacing the macOS-only afplay
// subprocess pipeline. Files live under web/assets/audio/. Missing files are
// tolerated silently (the app stays playable without sound).

const SOURCES = {
  background: ['assets/audio/background.mp3', 'assets/audio/background.m4a', 'assets/audio/background.wav'],
  splash: ['assets/audio/splash.mp3', 'assets/audio/splash.m4a', 'assets/audio/splash.wav'],
  flash: ['assets/audio/bozo.mp3', 'assets/audio/bozo.m4a', 'assets/audio/flash.mp3'],
  break: ['assets/audio/break.mp3', 'assets/audio/break.m4a', 'assets/audio/break.wav'],
};

let bg = null;
const sfx = {};

function makeAudio(sources, { loop = false, volume = 1 } = {}) {
  const a = new Audio();
  a.loop = loop;
  a.volume = volume;
  for (const src of sources) {
    const type = src.endsWith('.mp3') ? 'audio/mpeg'
      : src.endsWith('.m4a') ? 'audio/mp4'
      : src.endsWith('.wav') ? 'audio/wav' : '';
    if (!type || a.canPlayType(type)) { a.src = src; break; }
  }
  return a;
}

export function initAudio() {
  bg = makeAudio(SOURCES.background, { loop: true, volume: 0 });
  for (const key of ['splash', 'flash', 'break']) sfx[key] = makeAudio(SOURCES[key], { volume: 0.9 });
}

export function playBg() {
  if (!bg) return;
  bg.currentTime = 0;
  const p = bg.play();
  if (p && p.catch) p.catch(() => {});
  const target = 0.5;
  const start = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - start) / 2000);
    bg.volume = target * k;
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export function stopBg() {
  if (bg) { bg.pause(); bg.currentTime = 0; }
}

export function playSfx(name) {
  const a = sfx[name];
  if (!a || !a.src) return;
  try { a.currentTime = 0; const p = a.play(); if (p && p.catch) p.catch(() => {}); }
  catch (_) { /* no-op */ }
}
