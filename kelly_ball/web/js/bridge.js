// Thin wrapper around the pywebview JS API.
//
// pywebview injects `window.pywebview.api` and fires `pywebviewready` once
// the Python bridge is available. We await that, then expose helpers. When
// opened in a plain browser (no pywebview) we fall back to an in-memory mock
// so the UI can still be developed/tested.

let _ready = null;

function waitForPywebview() {
  if (window.pywebview && window.pywebview.api) return Promise.resolve(window.pywebview.api);
  return new Promise((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      if (window.pywebview && window.pywebview.api) { settled = true; resolve(window.pywebview.api); }
    };
    window.addEventListener('pywebviewready', done);
    const t = setInterval(() => {
      if (window.pywebview && window.pywebview.api) { clearInterval(t); done(); }
    }, 50);
    setTimeout(() => clearInterval(t), 4000);
  });
}

export function ready() {
  if (!_ready) {
    _ready = Promise.race([
      waitForPywebview(),
      new Promise((res) => setTimeout(() => res(null), 1500)),
    ]).then((a) => a || makeMock());
  }
  return _ready;
}

// Proxy so callers can `api.start_draw(...)` and it resolves lazily.
export const api = new Proxy({}, {
  get(_t, prop) {
    return async (...args) => {
      const a = await ready();
      const fn = a[prop];
      if (typeof fn !== 'function') throw new Error(`bridge: no API method "${String(prop)}"`);
      return fn(...args);
    };
  },
});

// ---- Browser-only mock (no Python) -----------------------------------
function makeMock() {
  console.warn('[bridge] pywebview not found — using in-memory mock.');
  const BALL_COLORS = {1:'#f5c518',2:'#1f6feb',3:'#e5484d',4:'#8b5cf6',5:'#f97316',6:'#16a34a',7:'#7f1d1d',8:'#111111',9:'#f5c518',10:'#1f6feb',11:'#e5484d',12:'#8b5cf6',13:'#f97316',14:'#16a34a',15:'#7f1d1d'};
  const colors = {}; for (const k in BALL_COLORS) colors[k] = BALL_COLORS[k];
  const state = {
    settings: { bozo_enabled:true, bozo_surprise_mode:false, background_music_enabled:true,
      whitelist:['marcus','markus','marco','marcos','marc','mark','mitchell','mitchel','mitch'] },
    assignments: [], index: 0, stage: 'name', winners: new Set(), tournament: false, round: 0,
  };
  const dn = (n) => {
    const s = state.settings;
    if (!s.bozo_enabled) return n;
    const t = n.trim();
    if (!t || t[0].toLowerCase() !== 'm') return n;
    if (s.whitelist.map(x=>x.toLowerCase()).includes(t.split(' ')[0].toLowerCase())) return n;
    return `BOZO ${n}`;
  };
  const sample = (k) => { const pool=[...Array(15)].map((_,i)=>i+1), out=[];
    for(let i=0;i<k;i++) out.push(pool.splice(Math.floor(Math.random()*pool.length),1)[0]); return out; };
  const revealState = () => {
    if (state.index >= state.assignments.length) return { view:'summary', ...summary() };
    const [name, ball] = state.assignments[state.index];
    const bozo = dn(name) !== name;
    return { view:'reveal', stage: state.stage, index: state.index, total: state.assignments.length,
      name, shown_name: state.settings.bozo_surprise_mode ? name : dn(name), display_name: dn(name),
      ball, is_bozo: bozo, surprise_mode: state.settings.bozo_surprise_mode,
      show_bozo_flash: state.stage==='ball' && bozo,
      tournament_mode: state.tournament, tournament_round: state.round };
  };
  const summary = () => ({ tournament_mode: state.tournament, tournament_round: state.round,
    can_late_join: state.assignments.length < 15,
    players: state.assignments.map(([name,ball])=>({ name, display_name: dn(name), ball, winner: state.winners.has(name) })) });
  return {
    get_bootstrap: async () => ({ max_players:15, ball_colors:colors,
      palette:{bg:'#0f1115',fg:'#f5f7fa',accent:'#22c55e',muted:'#9aa3af',panel:'#1a1d24',line:'#2a2f3a',dim:'#5a6370',danger:'#e5484d',bozo:'#fbbf24'},
      settings: state.settings, recents: [], default_chips: [] }),
    recents: async () => [],
    forget: async () => true,
    forget_all: async () => ({ forgotten: 0 }),
    display_name: async (n) => dn(n),
    start_draw: async (names, t=false) => {
      const ns = names.map(s=>s.trim()).filter(Boolean); const balls = sample(ns.length);
      state.assignments = ns.map((n,i)=>[n,balls[i]]);
      state.index=0; state.stage='name'; state.winners=new Set(); state.tournament=t; state.round=t?1:0;
      return revealState();
    },
    reveal_state: async () => revealState(),
    advance_reveal: async () => { if (state.stage==='name') state.stage='ball'; else { state.index++; state.stage='name'; } return revealState(); },
    mark_bozo_flash_shown: async () => {},
    cancel_draw: async () => { state.assignments=[]; state.index=0; state.stage='name'; return {ok:true}; },
    summary_state: async () => summary(),
    toggle_winner: async (name) => { if (state.winners.has(name)) state.winners.delete(name); else state.winners.add(name); return { name, winner: state.winners.has(name) }; },
    add_late_player: async (name) => {
      const used = new Set(state.assignments.map(a=>a[1]));
      const avail=[...Array(15)].map((_,i)=>i+1).filter(b=>!used.has(b));
      if (!avail.length || state.assignments.some(a=>a[0].toLowerCase()===name.toLowerCase())) return { error:'Could not add player' };
      const ball=avail[Math.floor(Math.random()*avail.length)]; state.assignments.push([name,ball]); return { name, ball, ...summary() };
    },
    can_advance: async () => { const w=state.assignments.filter(a=>state.winners.has(a[0]));
      if(!w.length) return {ok:false,message:'Mark at least one winner'};
      if(w.length===state.assignments.length) return {ok:false,message:'Need at least one loser'}; return {ok:true,message:''}; },
    next_round: async () => { const adv=state.assignments.filter(a=>state.winners.has(a[0])).map(a=>a[0]);
      if (adv.length<2) return { view:'champion', name: adv[0]||null, display_name: adv[0]?dn(adv[0]):null };
      state.round++; const balls=sample(adv.length); state.assignments=adv.map((n,i)=>[n,balls[i]]);
      state.index=0; state.stage='name'; state.winners=new Set(); return revealState(); },
    stats: async () => ({ players_known:0, total_appearances:0, total_wins:0, top_winners:[], most_games:[] }),
    save_settings: async (c) => { Object.assign(state.settings, c); return state.settings; },
  };
}
