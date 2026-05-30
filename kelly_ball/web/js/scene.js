// The 3D pool room — renderer, lighting, table, and reveal staging.
//
// Realism comes from three layers:
//   1. Image-based lighting: RoomEnvironment baked through PMREMGenerator
//      gives glossy balls real reflections with no external .hdr asset
//      (keeps the app fully offline / standalone).
//   2. MeshPhysicalMaterial clearcoat balls (balls.js) under a focused
//      billiard SpotLight + ACES filmic tone mapping.
//   3. A cinematic post stack: RenderPass → UnrealBloom → OutputPass.
//
// Public API (used by app.js): init, playIntro, onScreen, revealBall, confetti,
// bozoGlitch.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';

import { createBall, BALL_RADIUS } from './balls.js';

let renderer, scene, camera, composer, bloom, controls, clock;
let table, lamp, heroBall = null;
let title = null, titleFlickers = [];
let decoys = [];
let confettiSystem = null;
let boot = null;

// Bloom tuning. BASE keeps the dim room subtle; SPLASH lifts the halo so the
// neon title glows; REVEAL is the (now restrained) per-ball pop.
const BLOOM_BASE = 0.32;
const BLOOM_SPLASH = 0.7;
const BLOOM_REVEAL = 0.4;

// Time-driven updaters; each returns false when finished and is removed.
const updaters = [];

const TABLE_W = 9;     // along x (felt playing area, world units)
const TABLE_L = 4.6;   // along z

// True-to-life ball : table ratio. A real 2.25" ball is ~1/44 of a 9-ft table's
// 100" length (0.0225); createBall() makes a 1.0-diameter ball, so on our
// TABLE_W=9 felt a realistic loose ball is ~0.0225*9 ≈ 0.2 across. Used for the
// scattered "table" balls; the hero reveal ball stays full-size for legibility.
const BALL_SCALE = 0.2;
const FELT_TOP = -0.25;   // felt surface y (felt centre -0.5 + half its 0.5 height)

export async function init(canvas, bootData) {
  boot = bootData;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.82;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(boot.palette.bg);
  scene.fog = new THREE.Fog(new THREE.Color(boot.palette.bg), 14, 30);

  camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.set(0, 6.2, 9.5);
  camera.lookAt(0, 0.6, 0);

  // Image-based lighting (reflections) — procedural, no external file.
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  buildRoom();
  buildTable();
  await buildTitle();

  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  bloom = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight), BLOOM_BASE, 0.6, 0.9);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.6, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enablePan = false;
  controls.minDistance = 5;
  controls.maxDistance = 16;
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = Math.PI / 2.05;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.4;

  clock = new THREE.Clock();
  window.addEventListener('resize', onResize);
  animate();
}

function buildRoom() {
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshStandardMaterial({ color: 0x14171d, roughness: 0.85 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1.4;
  floor.receiveShadow = true;
  scene.add(floor);

  const wall = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 30),
    new THREE.MeshStandardMaterial({ color: 0x0d1014, roughness: 1.0 }));
  wall.position.set(0, 4, -14);
  scene.add(wall);

  // Hanging billiard lamp — the hero light.
  const lampGroup = new THREE.Group();
  const shade = new THREE.Mesh(
    new THREE.CylinderGeometry(2.4, 3.0, 1.0, 32, 1, true),
    new THREE.MeshStandardMaterial({ color: 0x1b1e24, roughness: 0.5, metalness: 0.4, side: THREE.DoubleSide }));
  shade.position.y = 7.2;
  lampGroup.add(shade);
  const bulb = new THREE.Mesh(
    new THREE.SphereGeometry(0.5, 24, 16),
    new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff1d0, emissiveIntensity: 1.6 }));
  bulb.position.y = 6.9;
  lampGroup.add(bulb);
  scene.add(lampGroup);

  lamp = new THREE.SpotLight(0xfff2d6, 350, 30, Math.PI / 4.5, 0.5, 1.6);
  lamp.position.set(0, 7.0, 0);
  lamp.target.position.set(0, 0, 0);
  lamp.castShadow = true;
  lamp.shadow.mapSize.set(2048, 2048);
  lamp.shadow.bias = -0.0004;
  scene.add(lamp);
  scene.add(lamp.target);

  scene.add(new THREE.HemisphereLight(0x4a5568, 0x0a0c10, 0.45));
}

function buildTable() {
  table = new THREE.Group();

  const felt = new THREE.Mesh(
    new THREE.BoxGeometry(TABLE_W, 0.5, TABLE_L),
    new THREE.MeshStandardMaterial({ color: 0x0b6b3a, roughness: 0.95 }));
  felt.position.y = -0.5;
  felt.receiveShadow = true;
  table.add(felt);

  const railMat = new THREE.MeshStandardMaterial({ color: 0x5a3315, roughness: 0.45, metalness: 0.1 });
  const railH = 0.45, railT = 0.55;
  const longRail = new THREE.BoxGeometry(TABLE_W + railT * 2, railH, railT);
  const shortRail = new THREE.BoxGeometry(railT, railH, TABLE_L + railT * 2);
  const r1 = new THREE.Mesh(longRail, railMat); r1.position.set(0, -0.25, TABLE_L / 2 + railT / 2);
  const r2 = new THREE.Mesh(longRail, railMat); r2.position.set(0, -0.25, -TABLE_L / 2 - railT / 2);
  const r3 = new THREE.Mesh(shortRail, railMat); r3.position.set(TABLE_W / 2 + railT / 2, -0.25, 0);
  const r4 = new THREE.Mesh(shortRail, railMat); r4.position.set(-TABLE_W / 2 - railT / 2, -0.25, 0);
  for (const r of [r1, r2, r3, r4]) { r.castShadow = true; r.receiveShadow = true; table.add(r); }

  const pocketMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 1 });
  const px = TABLE_W / 2 - 0.1, pz = TABLE_L / 2 - 0.1;
  for (const [x, z] of [[-px, -pz], [px, -pz], [-px, pz], [px, pz], [0, -pz], [0, pz]]) {
    const pk = new THREE.Mesh(new THREE.CircleGeometry(0.42, 24), pocketMat);
    pk.rotation.x = -Math.PI / 2;
    pk.position.set(x, -0.24, z);
    table.add(pk);
  }

  scene.add(table);
}

// ---- neon 3D title ---------------------------------------------------------
// "BOZO" / "BALL" as extruded, emissive letters that read as a glowing bar
// sign once UnrealBloom lifts the halo. Built per-letter so individual letters
// can flicker like a real neon tube.
const FONT_URL = new URL('../fonts/helvetiker_bold.typeface.json', import.meta.url).href;
let titleT = 0, titlePowerOn = 0;

async function buildTitle() {
  let font;
  try {
    font = await new FontLoader().loadAsync(FONT_URL);
  } catch (e) {
    console.warn('[scene] neon title font failed to load:', e);
    return;   // app.js leaves the HTML brand visible as a fallback
  }
  title = new THREE.Group();
  titleFlickers = [];
  const lines = [
    { text: 'BOZO', color: 0x22c55e, y: 0.78 },   // electric green
    { text: 'BALL', color: 0xfbbf24, y: -0.78 },   // amber
  ];
  for (const ln of lines) {
    const g = buildNeonLine(font, ln.text, ln.color);
    g.position.y = ln.y;
    title.add(g);
  }
  title.position.set(0, 3.3, 0);
  title.visible = false;
  scene.add(title);
  updaters.push((dt) => { updateTitle(dt); return true; });   // persistent
  window.__TITLE_OK = true;   // smoke-test flag: neon title font loaded + built
}

function buildNeonLine(font, text, color) {
  const g = new THREE.Group();
  const size = 1.15, gap = 0.16;
  const metas = [];
  let totalW = 0;
  for (const ch of text) {
    // NB: TextGeometry forces depth=50 if neither `depth` nor `height` is
    // given (TextGeometry.js:44) — always pass an explicit `depth`.
    const geo = new TextGeometry(ch, {
      font, size, depth: 0.32, curveSegments: 8,
      bevelEnabled: true, bevelThickness: 0.07, bevelSize: 0.05, bevelSegments: 3,
    });
    geo.computeBoundingBox();
    const bb = geo.boundingBox;
    const w = bb.max.x - bb.min.x;
    geo.translate(-bb.min.x, -size * 0.5, 0);   // x to 0, vertically centred
    metas.push({ geo, w });
    totalW += w + gap;
  }
  totalW -= gap;
  let x = -totalW / 2;
  for (const m of metas) {
    const mat = new THREE.MeshStandardMaterial({
      color, emissive: color, emissiveIntensity: 2.2,
      metalness: 0.1, roughness: 0.4,
    });
    const mesh = new THREE.Mesh(m.geo, mat);
    mesh.position.x = x;
    g.add(mesh);
    x += m.w + gap;
    titleFlickers.push({ mat, base: 2.2, phase: Math.random() * 10 });
  }
  return g;
}

function updateTitle(dt) {
  if (!title || !title.visible) return;
  titleT += dt;
  // Quick, smooth power-on ramp (~0.5s) — no random blinking.
  if (titlePowerOn < 1) titlePowerOn = Math.min(1, titlePowerOn + dt / 0.5);
  const ramp = 1 - Math.pow(1 - titlePowerOn, 3);   // ease-out
  // gentle idle sway/bob so the sign feels alive but stays readable head-on.
  title.rotation.y = Math.sin(titleT * 0.5) * 0.07;
  title.position.y = 3.3 + Math.sin(titleT * 0.9) * 0.05;
  for (const f of titleFlickers) {
    // Steady glow with only a very subtle slow breathe (±8%), per-letter phase.
    const breathe = 1 + 0.08 * Math.sin(titleT * 0.8 + f.phase);
    f.mat.emissiveIntensity = f.base * ramp * breathe;
  }
}

function setTitleVisible(show) {
  if (!title) return;
  if (show && !title.visible) titlePowerOn = 0;   // replay power-on each splash
  title.visible = show;
}

export function onScreen(name) {
  if (!controls) return;
  const splash = name === 'splash';
  // Splash reads head-on (no drift); setup/champion keep the slow showcase orbit.
  controls.autoRotate = (name === 'setup' || name === 'champion');
  setTitleVisible(splash);
  if (bloom) bloom.strength = splash ? BLOOM_SPLASH : BLOOM_BASE;
  if (name !== 'reveal') {
    clearHero();
    controls.target.set(0, 0.6, 0);
  }
}

function clearHero() {
  if (heroBall) { scene.remove(heroBall); heroBall = null; }
  for (const d of decoys) scene.remove(d);
  decoys = [];
}

// Clear the table between players so the next player can't see the prior ball
// (called by app.js on the "NEXT PLAYER COMING UP" name stage).
export function hideBall() {
  clearHero();
}

function scatterDecoys() {
  for (const d of decoys) scene.remove(d);
  decoys = [];
  const restY = FELT_TOP + BALL_RADIUS * BALL_SCALE;   // sit on the felt at true-to-life size
  const used = new Set();
  for (let i = 0; i < 5; i++) {
    let n; do { n = 1 + Math.floor(Math.random() * 15); } while (used.has(n));
    used.add(n);
    const b = createBall(n, boot.ball_colors);
    b.position.set((Math.random() - 0.5) * (TABLE_W - 2), restY,
                   (Math.random() - 0.5) * (TABLE_L - 1.4));
    b.scale.setScalar(BALL_SCALE);
    decoys.push(b);
    scene.add(b);
  }
}

// Gently glide the camera/target to a framing over a short duration.
function easeCamera(toPos, toTarget, dur) {
  const fromPos = camera.position.clone();
  const fromTgt = controls.target.clone();
  let s = 0;
  updaters.push((dt) => {
    s = Math.min(1, s + dt / dur);
    const e = 1 - Math.pow(1 - s, 3);
    camera.position.lerpVectors(fromPos, toPos, e);
    controls.target.lerpVectors(fromTgt, toTarget, e);
    return s < 1;
  });
}

// Reveal the assigned ball: it appears already facing the camera and eases
// quickly into focus, number forward, with minimal motion so it's instantly
// readable. Resolves once it settles (app.js uses this to unlock "Next").
export function revealBall(ball) {
  clearHero();
  scatterDecoys();

  const b = createBall(ball, boot.ball_colors);
  const heroY = 1.5;
  b.position.set(0, heroY + 0.6, 0);   // just above its resting spot
  b.scale.setScalar(0.6);
  scene.add(b);
  heroBall = b;
  b.lookAt(camera.position);   // disc (local +Z) faces the camera from frame 1
  bloom.strength = BLOOM_REVEAL;

  // Frame the hero ball at a comfortable, slightly-above-eye-level angle so the
  // upright number disc is legible; orbit stays enabled and the ball tracks it.
  easeCamera(new THREE.Vector3(0, heroY + 1.0, 6.6),
             new THREE.Vector3(0, heroY, 0), 0.6);

  return new Promise((resolve) => {
    const DUR = 0.5;
    let s = 0, t = 0, settled = false;

    updaters.push((dt) => {
      t += dt;
      if (!settled) {
        s = Math.min(1, s + dt / DUR);
        const e = 1 - Math.pow(1 - s, 3);          // ease-out: quick into focus
        b.position.y = heroY + 0.6 * (1 - e);       // small drop into place
        b.scale.setScalar(0.6 + 0.4 * e);           // subtle "pop" to full size
        b.lookAt(camera.position);                  // number faces the camera
        if (s >= 1) { settled = true; bloom.strength = BLOOM_BASE; resolve(); }
        return true;
      }
      // Calm idle: a tiny bob; number stays facing the camera even on orbit.
      b.position.y = heroY + Math.sin(t * 1.4) * 0.04;
      b.lookAt(camera.position);
      return true;   // keep bobbing until the screen changes (clearHero)
    });
  });
}

export function confetti() {
  const COUNT = 220;
  const colors = ['#22c55e', '#fbbf24', '#e5484d', '#1f6feb', '#8b5cf6', '#f97316'];
  const geo = new THREE.PlaneGeometry(0.12, 0.18);
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 0.5, metalness: 0.1 });
  const mesh = new THREE.InstancedMesh(geo, mat, COUNT);
  mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(COUNT * 3), 3);
  const parts = [];
  const dummy = new THREE.Object3D();
  const c = new THREE.Color();
  for (let i = 0; i < COUNT; i++) {
    parts.push({
      p: new THREE.Vector3((Math.random() - 0.5) * 10, 8 + Math.random() * 4, (Math.random() - 0.5) * 6),
      v: new THREE.Vector3((Math.random() - 0.5) * 1.5, -2 - Math.random() * 2, (Math.random() - 0.5) * 1.5),
      r: new THREE.Vector3(Math.random() * 6, Math.random() * 6, Math.random() * 6),
      w: new THREE.Vector3((Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6),
    });
    c.set(colors[i % colors.length]);
    mesh.setColorAt(i, c);
  }
  if (confettiSystem) scene.remove(confettiSystem);
  confettiSystem = mesh;
  scene.add(mesh);

  let life = 0;
  updaters.push((dt) => {
    life += dt;
    for (let i = 0; i < COUNT; i++) {
      const pt = parts[i];
      pt.v.y -= 3 * dt;
      pt.p.addScaledVector(pt.v, dt);
      pt.r.addScaledVector(pt.w, dt);
      dummy.position.copy(pt.p);
      dummy.rotation.set(pt.r.x, pt.r.y, pt.r.z);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (life > 5) { scene.remove(mesh); confettiSystem = null; return false; }
    return true;
  });
}

export function bozoGlitch() {
  let t = 0;
  const baseStrength = bloom.strength;
  const basePos = camera.position.clone();
  updaters.push((dt) => {
    t += dt;
    bloom.strength = baseStrength + 1.6 * Math.max(0, 1 - t / 0.5);
    const s = 0.12 * Math.max(0, 1 - t / 0.45);
    camera.position.set(
      basePos.x + (Math.random() - 0.5) * s,
      basePos.y + (Math.random() - 0.5) * s,
      basePos.z + (Math.random() - 0.5) * s);
    if (t > 0.5) { bloom.strength = baseStrength; camera.position.copy(basePos); return false; }
    return true;
  });
}

// ---- cinematic break intro -------------------------------------------------
// Racked balls → a cue strikes the break → real rigid-body physics scatters
// them → the neon title powers on. Runs before the splash and resolves when it
// finishes or is skipped (any click/key). Physics via the vendored cannon-es;
// if it can't load, the intro is skipped and the app falls through to splash.

// A tapered maple cue, oriented so its thin (blue-chalked) tip points toward +X.
function buildCueStick() {
  const g = new THREE.Group();
  const len = 7;
  const shaft = new THREE.Mesh(
    new THREE.CylinderGeometry(0.045, 0.08, len, 20, 1),
    new THREE.MeshStandardMaterial({ color: 0xd9b38c, roughness: 0.45, metalness: 0.05, transparent: true }));
  shaft.castShadow = true;
  const butt = new THREE.Mesh(
    new THREE.CylinderGeometry(0.08, 0.085, len * 0.32, 20, 1),
    new THREE.MeshStandardMaterial({ color: 0x1c140e, roughness: 0.5, metalness: 0.1, transparent: true }));
  butt.position.y = -len / 2 + (len * 0.32) / 2;   // toward the butt (-Y → -X) end
  const tip = new THREE.Mesh(
    new THREE.CylinderGeometry(0.045, 0.045, 0.12, 16, 1),
    new THREE.MeshStandardMaterial({ color: 0x2b6cb0, roughness: 0.6, transparent: true }));
  tip.position.y = len / 2 + 0.06;                 // thin striking tip (+Y → +X)
  g.add(shaft, butt, tip);
  g.rotation.z = -Math.PI / 2;                     // lay the cue along +X
  return g;
}

// A quick puff of pale-blue chalk dust at the cue-ball contact point.
function chalkPuff(pos) {
  const COUNT = 36;
  const geo = new THREE.PlaneGeometry(0.06, 0.06);
  const mat = new THREE.MeshBasicMaterial({
    color: 0xbcd2e8, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false });
  const mesh = new THREE.InstancedMesh(geo, mat, COUNT);
  const dummy = new THREE.Object3D();
  const parts = [];
  for (let i = 0; i < COUNT; i++) {
    parts.push({
      p: pos.clone(),
      v: new THREE.Vector3((Math.random() - 0.5) * 2.2, Math.random() * 1.6, (Math.random() - 0.5) * 2.2),
    });
  }
  scene.add(mesh);
  let life = 0;
  updaters.push((dt) => {
    life += dt;
    for (let i = 0; i < COUNT; i++) {
      const pt = parts[i];
      pt.v.y -= 2.5 * dt;
      pt.p.addScaledVector(pt.v, dt);
      dummy.position.copy(pt.p);
      dummy.scale.setScalar(1 + life * 2);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mat.opacity = Math.max(0, 0.9 * (1 - life / 0.6));
    if (life > 0.6) { scene.remove(mesh); geo.dispose(); mat.dispose(); return false; }
    return true;
  });
}

export async function playIntro({ onStrike } = {}) {
  if (!scene || !camera || !controls) return;

  // Take the scene over for the cinematic: no user orbit, title hidden, dim bloom.
  const prevAuto = controls.autoRotate;
  controls.autoRotate = false;
  controls.enabled = false;
  setTitleVisible(false);
  if (bloom) bloom.strength = BLOOM_BASE;
  camera.position.set(3.6, 1.15, 3.4);     // low, tight 3/4 on the racked balls
  controls.target.set(1.8, 0.35, 0);

  let CANNON;
  try {
    CANNON = await import('cannon-es');
  } catch (e) {
    console.warn('[scene] physics engine unavailable — skipping intro:', e);
    controls.enabled = true;
    controls.autoRotate = prevAuto;
    return;
  }

  // Timeline (seconds from intro start).
  const DRAW_T = 1.3, BACK_T = 2.5, STRIKE_T = 2.8, CONTACT_T = 2.92, FOLLOW_END = 3.2;
  const CRANE_T = 3.5, REVEAL_T = 5.0, FADE_T = 5.5, FADE_DUR = 0.9, END_T = 6.6;
  // The intro balls sit a touch smaller (radius BR) so the full 15-ball triangle
  // fits across this narrow table; they're gone before any full-size ball shows.
  const BSCALE = 0.84, BR = BALL_RADIUS * BSCALE;
  const REST_Y = BR + FELT_TOP;   // ball-centre rest height
  const HALF_LEN = 3.5;
  const ease = (s) => 1 - Math.pow(1 - s, 3);   // ease-out cubic
  const easeIn = (s) => s * s * s;              // ease-in cubic
  const clamp01 = (s) => Math.max(0, Math.min(1, s));

  // Physics world: gravity, felt (ground), four rails, billiard contact tuning.
  const world = new CANNON.World({ gravity: new CANNON.Vec3(0, -9.82, 0) });
  world.allowSleep = false;
  world.solver.iterations = 20;   // 15 stacked contacts need extra solver passes
  const ballPMat = new CANNON.Material('ball');
  const railPMat = new CANNON.Material('rail');
  const groundPMat = new CANNON.Material('ground');
  world.addContactMaterial(new CANNON.ContactMaterial(ballPMat, ballPMat, { friction: 0.04, restitution: 0.92 }));
  world.addContactMaterial(new CANNON.ContactMaterial(ballPMat, railPMat, { friction: 0.1, restitution: 0.75 }));
  world.addContactMaterial(new CANNON.ContactMaterial(ballPMat, groundPMat, { friction: 0.3, restitution: 0.2 }));

  const ground = new CANNON.Body({ type: CANNON.Body.STATIC, shape: new CANNON.Plane(), material: groundPMat });
  ground.quaternion.setFromEuler(-Math.PI / 2, 0, 0);   // normal +Y
  ground.position.set(0, FELT_TOP, 0);
  world.addBody(ground);

  const HX = TABLE_W / 2, HZ = TABLE_L / 2;
  const addWall = (x, z, angle) => {
    const b = new CANNON.Body({ type: CANNON.Body.STATIC, shape: new CANNON.Plane(), material: railPMat });
    b.quaternion.setFromAxisAngle(new CANNON.Vec3(0, 1, 0), angle);
    b.position.set(x, 0, z);
    world.addBody(b);
  };
  addWall(-HX, 0, Math.PI / 2);    // left rail  (normal +X)
  addWall(HX, 0, -Math.PI / 2);    // right rail (normal -X)
  addWall(0, -HZ, 0);              // far rail   (normal +Z)
  addWall(0, HZ, Math.PI);         // near rail  (normal -Z)

  const items = [];      // { body, mesh }
  const fadeMats = [];
  const mkBody = (x, z) => new CANNON.Body({
    mass: 1, shape: new CANNON.Sphere(BR), material: ballPMat,
    position: new CANNON.Vec3(x, REST_Y, z), linearDamping: 0.55, angularDamping: 0.6,
  });

  // Triangle rack (apex toward the cue ball), 8-ball centred. A clear gap keeps
  // the rack contact-free at rest so it doesn't pop when stepping begins.
  const RACK_ORDER = [1, 14, 2, 3, 8, 11, 6, 12, 9, 4, 5, 13, 7, 15, 10];
  const apexX = 0.6, rowDx = BR * Math.sqrt(3) + 0.03, colDz = BR * 2 + 0.03;
  let oi = 0;
  for (let row = 0; row < 5; row++) {
    for (let j = 0; j <= row; j++) {
      const n = RACK_ORDER[oi++];
      const x = apexX + row * rowDx, z = (j - row / 2) * colDz;
      const mesh = createBall(n, boot.ball_colors);
      mesh.material = mesh.material.clone();   // own material so we can fade it out
      mesh.material.transparent = true;
      mesh.scale.setScalar(BSCALE);
      mesh.position.set(x, REST_Y, z);
      scene.add(mesh);
      fadeMats.push(mesh.material);
      const body = mkBody(x, z);
      world.addBody(body);
      items.push({ body, mesh });
    }
  }

  // Cue ball at the head spot.
  const cueX = -3.0;
  const cueMesh = new THREE.Mesh(
    new THREE.SphereGeometry(BR, 48, 32),
    new THREE.MeshPhysicalMaterial({ color: 0xf7f7f2, clearcoat: 1, clearcoatRoughness: 0.06,
      roughness: 0.16, metalness: 0, envMapIntensity: 1.25, transparent: true }));
  cueMesh.castShadow = cueMesh.receiveShadow = true;
  cueMesh.position.set(cueX, REST_Y, 0);
  scene.add(cueMesh);
  fadeMats.push(cueMesh.material);
  const cueBody = mkBody(cueX, 0);
  world.addBody(cueBody);
  items.push({ body: cueBody, mesh: cueMesh });

  // Cue stick (visual only; the strike is applied as a velocity to the cue ball).
  const cueStick = buildCueStick();
  cueStick.position.set(0, REST_Y, 0);
  scene.add(cueStick);
  cueStick.traverse((o) => { if (o.material) fadeMats.push(o.material); });

  window.__INTRO_OK = true;   // smoke-test flag: intro built + running

  const POCKETS = [[-4.4, -2.2], [4.4, -2.2], [-4.4, 2.2], [4.4, 2.2], [0, -2.2], [0, 2.2]];
  const POCKET_R2 = 0.5 * 0.5;

  return new Promise((resolve) => {
    let T = 0, stepping = false, finished = false;

    // Cue tip x over the timeline: rest → draw back → thrust → follow-through.
    const cueTipX = (t) => {
      const REST = -3.54, BACK = -4.75, CONTACT = -3.44, FOLLOW = -3.05;
      if (t < DRAW_T) return REST;
      if (t < BACK_T) return REST + (BACK - REST) * ease(clamp01((t - DRAW_T) / (BACK_T - DRAW_T)));
      if (t < STRIKE_T) return BACK;
      if (t < CONTACT_T) return BACK + (CONTACT - BACK) * easeIn(clamp01((t - STRIKE_T) / (CONTACT_T - STRIKE_T)));
      if (t < FOLLOW_END) return CONTACT + (FOLLOW - CONTACT) * clamp01((t - CONTACT_T) / (FOLLOW_END - CONTACT_T));
      return FOLLOW;
    };

    const checkPockets = () => {
      for (const it of items) {
        if (it.mesh.userData.sunk) continue;
        const p = it.body.position;
        for (const [px, pz] of POCKETS) {
          const dx = p.x - px, dz = p.z - pz;
          if (dx * dx + dz * dz < POCKET_R2) {
            it.mesh.userData.sunk = true;
            try { world.removeBody(it.body); } catch (_) { /* already gone */ }
            break;
          }
        }
      }
    };

    const cleanup = () => {
      for (const it of items) {
        if (it.mesh.parent) scene.remove(it.mesh);
        it.mesh.geometry.dispose?.();
        it.mesh.material.dispose?.();   // cloned material — shared textures untouched
      }
      if (cueStick.parent) scene.remove(cueStick);
      cueStick.traverse((o) => { o.geometry?.dispose?.(); o.material?.dispose?.(); });
    };

    const finish = () => {
      if (finished) return;
      finished = true;
      window.removeEventListener('click', skip);
      window.removeEventListener('keydown', skip);
      cleanup();
      controls.enabled = true;
      controls.autoRotate = prevAuto;
      resolve();
    };

    // Any click/key fast-forwards to the end state (title up, splash framing).
    const skip = () => {
      camera.position.set(0, 6.2, 9.5);
      controls.target.set(0, 0.6, 0);
      setTitleVisible(true);
      if (bloom) bloom.strength = BLOOM_SPLASH;
      finish();
    };
    window.addEventListener('click', skip);
    window.addEventListener('keydown', skip);

    const events = [
      { at: CONTACT_T, hit: false, fn: () => {
          stepping = true;
          cueBody.velocity.set(16, 0, (Math.random() - 0.5) * 0.6);   // the break
          if (onStrike) onStrike();
          bozoGlitch();                                               // flare + shake
          chalkPuff(new THREE.Vector3(cueX - BR, REST_Y, 0));         // stick-side contact
        } },
      { at: CRANE_T, hit: false, fn: () =>
          easeCamera(new THREE.Vector3(0.5, 7.8, 8.5), new THREE.Vector3(1.2, 0.2, 0), 1.5) },
      { at: REVEAL_T, hit: false, fn: () => {
          setTitleVisible(true);
          if (bloom) bloom.strength = BLOOM_SPLASH;
          easeCamera(new THREE.Vector3(0, 6.2, 9.5), new THREE.Vector3(0, 0.6, 0), 1.5);
        } },
      { at: END_T, hit: false, fn: finish },
    ];

    updaters.push((dt) => {
      if (finished) return false;
      T += dt;
      for (const e of events) if (!e.hit && T >= e.at) { e.hit = true; e.fn(); }

      cueStick.position.x = cueTipX(T) - HALF_LEN;

      if (stepping) {
        world.step(1 / 60, dt, 4);
        for (const it of items) {
          if (it.mesh.userData.sunk) continue;
          const b = it.body;
          it.mesh.position.set(b.position.x, b.position.y, b.position.z);
          it.mesh.quaternion.set(b.quaternion.x, b.quaternion.y, b.quaternion.z, b.quaternion.w);
        }
        checkPockets();
      }

      // Sunk balls drop into the pocket and shrink away.
      for (const it of items) {
        if (it.mesh.userData.sunk && it.mesh.parent) {
          it.mesh.position.y -= 4 * dt;
          it.mesh.scale.multiplyScalar(Math.max(0, 1 - 2.5 * dt));
          if (it.mesh.position.y < -1.6) scene.remove(it.mesh);
        }
      }

      if (T >= FADE_T) {
        const o = Math.max(0, 1 - (T - FADE_T) / FADE_DUR);
        for (const m of fadeMats) m.opacity = o;
      }
      return true;
    });
  });
}

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  for (let i = updaters.length - 1; i >= 0; i--) {
    if (updaters[i](dt) === false) updaters.splice(i, 1);
  }
  if (controls) controls.update();
  composer.render();
}

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
}
