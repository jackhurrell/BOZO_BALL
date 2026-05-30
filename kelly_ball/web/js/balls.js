// Procedural billiard balls — a 3D port of drawing.py's ball logic.
//
// Each ball's number + stripe are painted onto an equirectangular canvas
// texture so they wrap correctly around a sphere: two number discs sit on
// opposite sides of the equator (like a real ball), stripes (9–15) get a
// coloured band around the middle third with white poles, solids (1–8) are
// fully coloured, and the 8-ball is black.

import * as THREE from 'three';

const BALL_RADIUS = 0.5;

const _texCache = new Map();
const _matCache = new Map();

function ballTexture(ball, ballColors) {
  if (_texCache.has(ball)) return _texCache.get(ball);

  const W = 1024, H = 512;
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  const color = ballColors[String(ball)] || '#666666';
  const striped = ball >= 9 && ball !== 8;

  if (striped) {
    ctx.fillStyle = '#f3f0e8';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = color;
    ctx.fillRect(0, H * 0.30, W, H * 0.40);
  } else {
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, W, H);
  }

  // Two number discs at u=0.25 and u=0.75 on the equator.
  const discR = H * 0.16;
  for (const cx of [W * 0.25, W * 0.75]) {
    const cy = H * 0.5;
    ctx.beginPath();
    ctx.fillStyle = '#f7f7f2';
    ctx.arc(cx, cy, discR, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#141414';
    ctx.font = `bold ${Math.round(discR * 1.15)}px Helvetica, Arial, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(ball), cx, cy + discR * 0.04);
  }

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  _texCache.set(ball, tex);
  return tex;
}

export function ballMaterial(ball, ballColors) {
  if (_matCache.has(ball)) return _matCache.get(ball);
  const mat = new THREE.MeshPhysicalMaterial({
    map: ballTexture(ball, ballColors),
    clearcoat: 1.0,            // lacquer coat: sharp highlight over body colour
    clearcoatRoughness: 0.06,
    roughness: 0.16,
    metalness: 0.0,
    envMapIntensity: 1.25,
    sheen: 0.2,
  });
  _matCache.set(ball, mat);
  return mat;
}

export function createBall(ball, ballColors) {
  const geo = new THREE.SphereGeometry(BALL_RADIUS, 64, 48);
  const mesh = new THREE.Mesh(geo, ballMaterial(ball, ballColors));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData.ball = ball;
  // Arbitrary start orientation; the hero ball is re-aimed via lookAt in
  // scene.js (decoys keep whatever orientation they land in).
  mesh.rotation.y = -Math.PI / 2;
  return mesh;
}

export { BALL_RADIUS };
