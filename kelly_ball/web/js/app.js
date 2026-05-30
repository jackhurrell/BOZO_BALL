// BOZO Ball — front-end flow controller.
//
// Mirrors the original Tkinter screen state machine
// (splash → setup → reveal[name→ball] → summary → tournament/champion)
// but renders via DOM overlays + a Three.js scene. All game RULES come from
// Python over the bridge; this file only orchestrates presentation.

import { api } from './bridge.js';
import { initAudio, playBg, stopBg, playSfx } from './audio.js';

let BOOT = null;
let chips = [];
let scene = null;
let REVEAL = null;
let settingsReturn = showSetup;

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};

const SCREENS = ['splash', 'setup', 'reveal', 'summary', 'stats', 'settings', 'champion'];
function show(name) {
  for (const s of SCREENS) $(`#screen-${s}`).hidden = (s !== name);
  if (scene) scene.onScreen(name);
}

let toastTimer = null;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2200);
}

// ---- boot ------------------------------------------------------------
async function boot() {
  BOOT = await api.get_bootstrap();
  applyPalette(BOOT.palette);
  initAudio();
  try {
    scene = await import('./scene.js');
    await scene.init($('#scene'), BOOT);
    // The 3D neon title replaces the HTML brand; CSS hides it when present.
    document.body.classList.add('has-scene');
  } catch (err) {
    console.warn('[app] 3D scene unavailable, using 2D fallback:', err);
    scene = null;
  }
  wireGlobalActions();
  // Cinematic break intro before the splash (skippable; toggled in Settings).
  if (scene && scene.playIntro && BOOT.settings.intro_enabled) {
    for (const s of SCREENS) $(`#screen-${s}`).hidden = true;   // bare 3D scene
    try { await scene.playIntro({ onStrike: () => playSfx('break') }); }
    catch (err) { console.warn('[app] intro failed:', err); }
  }
  showSplash();
  // Smoke-test flags set only after a successful bootstrap (bridge round-trip
  // + palette + audio + scene attempt). Lets a headless probe verify boot.
  window.__BOOT_OK = true;
  window.__SCENE_OK = !!scene;
}

function applyPalette(p) {
  if (!p) return;
  const r = document.documentElement.style;
  for (const [k, v] of Object.entries(p)) r.setProperty(`--${k}`, v);
}

// ---- splash ----------------------------------------------------------
function showSplash() {
  show('splash');
  playSfx('splash');
  const dismiss = () => {
    window.removeEventListener('click', dismiss);
    window.removeEventListener('keydown', dismiss);
    if (BOOT.settings.background_music_enabled) playBg();
    showSetup();
  };
  window.addEventListener('click', dismiss);
  window.addEventListener('keydown', dismiss);
}

// ---- setup -----------------------------------------------------------
async function showSetup() {
  show('setup');
  chips = BOOT.default_chips.slice();
  $('#tournament-toggle').checked = false;
  renderChips();
  await renderRecents();
  updateFooter();
  const input = $('#name-input');
  input.value = '';
  input.focus();
}

function renderChips() {
  const box = $('#chips');
  box.innerHTML = '';
  for (const name of chips) {
    const chip = el('span', 'chip');
    chip.append(document.createTextNode(name));
    const x = el('span', 'x', '✕');
    x.addEventListener('click', () => removeChip(name));
    chip.append(x);
    box.append(chip);
  }
}

async function renderRecents() {
  const wrap = $('#recents');
  wrap.innerHTML = '';
  const recents = await api.recents();
  const inGame = new Set(chips.map((n) => n.toLowerCase()));
  for (const r of recents) {
    const here = inGame.has(r.name.toLowerCase());
    const badge = r.wins > 0 ? `🏆${r.wins} ` : '';
    const btn = el('button', 'recent' + (here ? ' in-game' : ''),
      `${here ? '✗ ' : '+ '}${badge}${r.name}`);
    if (!here) btn.addEventListener('click', () => addChip(r.name));
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      if (confirm(`Forget "${r.name}"?`)) api.forget(r.name).then(renderRecents);
    });
    wrap.append(btn);
  }
}

async function clearRecents() {
  const recents = await api.recents();
  if (!recents.length) { toast('No recent names to clear'); return; }
  if (!confirm(`Forget all ${recents.length} recent players? This also clears their win/game stats.`)) return;
  await api.forget_all();
  await renderRecents();
  toast('Recent names cleared');
}

function addChip(name) {
  name = name.trim();
  if (!name) return;
  if (chips.some((n) => n.toLowerCase() === name.toLowerCase())) { toast(`${name} is already in the game`); return; }
  if (chips.length >= BOOT.max_players) { toast(`Max ${BOOT.max_players} players — Kelly pool only has 15 balls`); return; }
  chips.push(name);
  renderChips(); renderRecents(); updateFooter();
}

function removeChip(name) {
  chips = chips.filter((n) => n.toLowerCase() !== name.toLowerCase());
  renderChips(); renderRecents(); updateFooter();
}

function updateFooter() {
  const n = chips.length;
  const full = n >= BOOT.max_players;
  const c = $('#count');
  c.textContent = full ? `${n} of ${BOOT.max_players} playing — table is full` : `${n} of ${BOOT.max_players} playing`;
  c.style.color = full ? 'var(--danger)' : 'var(--muted)';
  $('#start-btn').disabled = n === 0;
}

function wireSetupInput() {
  const input = $('#name-input');
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const v = input.value.replace(/,$/, '').trim();
      input.value = '';
      if (v) addChip(v);
    } else if (e.key === 'Backspace' && !input.value && chips.length) {
      removeChip(chips[chips.length - 1]);
    }
  });
}

// ---- reveal ----------------------------------------------------------
async function startDraw() {
  const tournament = $('#tournament-toggle').checked;
  const res = await api.start_draw(chips, tournament);
  if (res.error) { toast(res.error); return; }
  REVEAL = res;
  renderReveal();
}

async function renderReveal() {
  const st = REVEAL;
  if (st.view === 'summary') return renderSummary(st);

  show('reveal');
  $('#reveal-progress').textContent = st.tournament_mode
    ? `Round ${st.tournament_round} • Player ${st.index + 1} of ${st.total}`
    : `Player ${st.index + 1} of ${st.total}`;
  const next = $('#next-btn');

  if (st.stage === 'name') {
    // Clear the previous player's ball so it's not visible during the handoff.
    if (scene && scene.hideBall) scene.hideBall();
    $('#reveal-kicker').textContent = 'NEXT PLAYER COMING UP';
    $('#reveal-name').textContent = st.shown_name;
    $('#reveal-name').hidden = false;
    $('#reveal-ball-slot').innerHTML = '';
    $('#reveal-hint').textContent = 'Pass the screen to this player, then click Next';
    next.disabled = false;
  } else {
    if (st.show_bozo_flash) {
      await bozoFlash(st);
      await api.mark_bozo_flash_shown();
    }
    $('#reveal-kicker').textContent = 'YOUR BALL';
    $('#reveal-name').hidden = true;
    $('#reveal-hint').textContent = 'Remember it! Then click Next.';
    next.disabled = true;
    await revealBall(st.ball);
    next.disabled = false;
  }
}

async function revealBall(ball) {
  const slot = $('#reveal-ball-slot');
  slot.innerHTML = '';
  if (scene && scene.revealBall) { await scene.revealBall(ball); return; }
  slot.append(make2dBall(ball));
  playSfx('flash');
}

function make2dBall(ball) {
  const color = BOOT.ball_colors[String(ball)] || '#666';
  const wrap = el('div', 'ball2d');
  if (ball >= 9 && ball !== 8) {
    wrap.style.background = '#fff';
    wrap.style.borderTop = `46px solid ${color}`;
    wrap.style.borderBottom = `46px solid ${color}`;
  } else {
    wrap.style.background = color;
  }
  wrap.append(el('div', 'disc', `<span>${ball}</span>`));
  return wrap;
}

function bozoFlash(st) {
  return new Promise((resolve) => {
    playSfx('flash');
    const overlay = el('div'); overlay.id = 'bozo-flash';
    overlay.append(el('div', 'clown', '🤡'));
    overlay.append(el('div', 'word', 'BOZO'));
    if (scene && scene.bozoGlitch) scene.bozoGlitch();
    document.body.append(overlay);
    const ms = st.surprise_mode ? 700 : 300;
    setTimeout(() => { overlay.remove(); resolve(); }, ms);
  });
}

async function advanceReveal() {
  REVEAL = await api.advance_reveal();
  renderReveal();
}

async function cancelReveal() {
  if (!confirm('Cancel this draw and return to the main screen?')) return;
  await api.cancel_draw();
  showSetup();
}

// ---- summary ---------------------------------------------------------
async function renderSummary(st) {
  show('summary');
  $('#summary-title').textContent = st.tournament_mode ? 'Round complete!' : 'All balls drawn';
  $('#summary-sub').textContent = st.tournament_mode
    ? 'Tap 🏆 next to the winners — they advance to the next round.'
    : 'Tap 🏆 to record a winner.';

  const list = $('#summary-list');
  list.innerHTML = '';
  for (const p of st.players) {
    const row = el('div', 'summary-row' + (p.winner ? ' winner' : ''));
    row.append(el('span', 'pname', p.display_name));
    const readout = el('span', 'ball-readout', '●●');
    const showBtn = el('button', 'text-btn', 'Hold to Show');
    const reveal = () => { readout.textContent = String(p.ball); readout.style.color = BOOT.ball_colors[String(p.ball)] || 'var(--fg)'; };
    const hide = () => { readout.textContent = '●●'; readout.style.color = 'var(--muted)'; };
    showBtn.addEventListener('mousedown', reveal);
    showBtn.addEventListener('mouseup', hide);
    showBtn.addEventListener('mouseleave', hide);
    const win = el('button', 'win-btn' + (p.winner ? ' on' : ''), '🏆');
    win.addEventListener('click', async () => {
      const r = await api.toggle_winner(p.name);
      win.classList.toggle('on', r.winner);
      row.classList.toggle('winner', r.winner);
    });
    row.append(showBtn, readout, win);
    list.append(row);
  }

  $('#late-join').hidden = !st.can_late_join;

  const foot = $('#summary-foot');
  foot.innerHTML = '';
  if (st.tournament_mode && st.players.length > 1) {
    const end = el('button', 'text-btn', 'End Tournament');
    end.addEventListener('click', showSetup);
    const nr = el('button', 'primary', 'Next Round →');
    nr.addEventListener('click', nextRound);
    foot.append(end, nr);
  } else {
    const ng = el('button', 'primary', 'New Game');
    ng.addEventListener('click', showSetup);
    foot.append(ng);
  }
}

async function addLatePlayer() {
  const input = $('#late-input');
  const name = input.value.trim();
  input.value = '';
  if (!name) return;
  const r = await api.add_late_player(name);
  if (r.error) { toast(r.error); return; }
  renderSummary(r);
}

async function nextRound() {
  const r = await api.next_round();
  if (r.error) { toast(r.error); return; }
  if (r.view === 'champion') return renderChampion(r);
  REVEAL = r;
  renderReveal();
}

// ---- champion --------------------------------------------------------
function renderChampion(r) {
  show('champion');
  $('#champion-name').textContent = r.display_name || '(no winner declared)';
  playSfx('flash');
  if (scene && scene.confetti) scene.confetti();
}

// ---- stats -----------------------------------------------------------
async function showStats() {
  show('stats');
  const s = await api.stats();
  const agg = $('#stats-agg');
  agg.innerHTML = '';
  for (const [k, v] of [
    ['Players known', s.players_known],
    ['Total player-appearances', s.total_appearances],
    ['Wins recorded', s.total_wins],
  ]) {
    const c = el('div', 'stat-cell');
    c.append(el('div', 'v', String(v)), el('div', 'k', k));
    agg.append(c);
  }
  const boards = $('#stats-boards');
  boards.innerHTML = '';
  const board = (title, rows) => {
    const b = el('div', 'board');
    b.append(el('h4', null, title));
    if (!rows.length) b.append(el('div', 'dim small', '— no data yet —'));
    for (const r of rows) {
      const row = el('div', 'brow');
      row.append(el('span', null, r.display_name), el('span', 'bv', String(r.value)));
      b.append(row);
    }
    return b;
  };
  boards.append(board('🏆 Top winners', s.top_winners), board('🎱 Most games', s.most_games));
}

// ---- settings --------------------------------------------------------
async function showSettings(returnTo) {
  settingsReturn = returnTo || showSetup;
  show('settings');
  const s = BOOT.settings;
  const mode = !s.bozo_enabled ? 'off' : (s.bozo_surprise_mode ? 'surprise' : 'classic');
  for (const r of document.querySelectorAll('input[name="bozo"]')) r.checked = (r.value === mode);
  $('#music-toggle').checked = !!s.background_music_enabled;
  $('#intro-toggle').checked = s.intro_enabled !== false;
  $('#whitelist').value = (s.whitelist || []).join('\n');
}

async function saveSettings() {
  const mode = document.querySelector('input[name="bozo"]:checked')?.value || 'classic';
  const wasMusic = !!BOOT.settings.background_music_enabled;
  const music = $('#music-toggle').checked;
  BOOT.settings = await api.save_settings({
    bozo_enabled: mode !== 'off',
    bozo_surprise_mode: mode === 'surprise',
    background_music_enabled: music,
    intro_enabled: $('#intro-toggle').checked,
    whitelist: $('#whitelist').value.split('\n').map((l) => l.trim()).filter(Boolean),
  });
  if (music && !wasMusic) playBg();
  else if (!music && wasMusic) stopBg();
  settingsReturn();
}

function resetSettings() {
  for (const r of document.querySelectorAll('input[name="bozo"]')) r.checked = (r.value === 'classic');
  $('#music-toggle').checked = true;
  $('#intro-toggle').checked = true;
  $('#whitelist').value = ['marcus','markus','marco','marcos','marc','mark','mitchell','mitchel','mitch'].join('\n');
}

// ---- global wiring ---------------------------------------------------
function wireGlobalActions() {
  wireSetupInput();
  $('#late-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') addLatePlayer(); });

  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    ({
      start: startDraw,
      cancel: cancelReveal,
      next: advanceReveal,
      stats: showStats,
      'clear-recents': clearRecents,
      settings: () => showSettings(showSetup),
      'settings-return': () => showSettings(() => renderSummary(REVEAL)),
      'settings-back': () => settingsReturn(),
      'settings-save': saveSettings,
      'settings-reset': resetSettings,
      'back-setup': showSetup,
      'late-add': addLatePlayer,
    }[btn.dataset.action] || (() => {}))();
  });
}

boot();
