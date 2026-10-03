// Interactive 3D models (e.g. tadpole skulls) that readers can spin and zoom.
//
// Used from a page like this (see education/posts/suctorial-tadpoles-1.qmd):
//
//   <div class="model-compare">
//     <div class="model-panes">
//       <figure class="model-pane">
//         <div class="model-stage" data-src="../../assets/models/name.bin"
//              role="img" aria-label="What the model shows"></div>
//         <figcaption>Label under this model</figcaption>
//       </figure>
//       ... more panes ...
//     </div>
//     <div class="model-bar">
//       <span class="model-hint">Drag to rotate ...</span>
//       <button type="button" class="model-reset">Reset view</button>
//     </div>
//   </div>
//   <script type="module" src="../../assets/js/model-viewer.js"></script>
//
// Models are .bin files made by scripts/make_web_model.py from an STL.
// All the models in one .model-compare box are drawn at the same scale and
// turn together, so they can be compared side by side. Nothing is downloaded
// until the box is about to scroll into view.

import * as THREE from "./three/three.module.min.js";
import { OrbitControls } from "./three/OrbitControls.js";

// Starting view: from above, in front and a little to the left. In the
// models, +y is dorsal (up) and +z is anterior (the snout). A figure can
// pick its own starting direction with data-start="x,y,z" on .model-compare.
const START_DIR = new THREE.Vector3(-0.55, 0.75, 0.9).normalize();
const START_DIST = 5.4;
const CARTILAGE = 0xddd3bd;

async function loadModel(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const buf = await res.arrayBuffer();
  const dv = new DataView(buf);
  const magic = String.fromCharCode(...new Uint8Array(buf, 0, 4));
  if (magic !== "TMSH") throw new Error(`${url} is not a model file`);
  const nVerts = dv.getUint32(8, true);
  const nIdx = dv.getUint32(12, true);
  const lo = [0, 1, 2].map((i) => dv.getFloat32(16 + 4 * i, true));
  const hi = [0, 1, 2].map((i) => dv.getFloat32(28 + 4 * i, true));
  let off = 40;
  const q = new Uint16Array(buf, off, nVerts * 3);
  off += nVerts * 6;
  const pos = new Float32Array(nVerts * 3);
  for (let i = 0; i < pos.length; i++) {
    const a = i % 3;
    pos[i] = lo[a] + (q[i] / 65535) * (hi[a] - lo[a]);
  }
  const idx = nVerts < 65536
    ? new Uint16Array(buf.slice(off, off + nIdx * 2))
    : new Uint32Array(buf.slice(off, off + nIdx * 4));
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geom.setIndex(new THREE.BufferAttribute(idx, 1));
  geom.computeVertexNormals();
  geom.computeBoundingBox();
  return geom;
}

function makePane(stage) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
  scene.add(camera);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2a2a, 0.9));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(-2, 2.5, 3);
  camera.add(key); // the lights follow the viewer, so the side you look at is lit
  const rim = new THREE.DirectionalLight(0xffffff, 0.6);
  rim.position.set(3, -1, -1);
  camera.add(rim);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.enableZoom = false; // switched on once the reader grabs the model
  controls.minDistance = 2;
  controls.maxDistance = 14;
  controls.autoRotateSpeed = 1.6;

  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  return {
    stage, renderer, scene, camera, controls,
    setMesh(geom) {
      const mat = new THREE.MeshStandardMaterial({ color: CARTILAGE, roughness: 0.62, metalness: 0 });
      scene.add(new THREE.Mesh(geom, mat));
    },
    render() { renderer.render(scene, camera); },
  };
}

function setUp(box) {
  const stages = Array.from(box.querySelectorAll(".model-stage"));
  let panes;
  try {
    panes = stages.map(makePane);
  } catch (err) {
    box.classList.add("has-error");
    console.error(err);
    return;
  }
  let active = panes[0];
  let running = false;
  const startDir = START_DIR.clone();
  if (box.dataset.start) {
    const v = box.dataset.start.split(",").map(Number);
    if (v.length === 3 && v.every(Number.isFinite)) startDir.set(v[0], v[1], v[2]).normalize();
  }

  function resetView() {
    for (const p of panes) {
      p.controls.target.set(0, 0, 0);
      p.camera.position.copy(startDir).multiplyScalar(START_DIST);
      p.camera.up.set(0, 1, 0);
      p.controls.update();
    }
  }

  function setAuto(on) {
    for (const p of panes) p.controls.autoRotate = on && p === active;
  }

  for (const p of panes) {
    p.controls.addEventListener("start", () => {
      active = p;
      setAuto(false);
    });
  }
  // Wheel-zoom only after the reader has grabbed a model, so scrolling down
  // the page past the figure doesn't get caught by it. Pinch works right away.
  box.addEventListener("pointerdown", () => panes.forEach((p) => (p.controls.enableZoom = true)));
  box.addEventListener("pointerleave", (e) => {
    if (e.pointerType === "mouse") panes.forEach((p) => (p.controls.enableZoom = false));
  });
  box.addEventListener("touchstart", () => panes.forEach((p) => (p.controls.enableZoom = true)), { passive: true });

  const reset = box.querySelector(".model-reset");
  if (reset) reset.addEventListener("click", () => { active = panes[0]; resetView(); setAuto(true); });

  function frame() {
    if (!running) return;
    active.controls.update();
    for (const p of panes) {
      if (p !== active) {
        p.camera.position.copy(active.camera.position);
        p.camera.quaternion.copy(active.camera.quaternion);
        p.controls.target.copy(active.controls.target);
      }
      p.render();
    }
    requestAnimationFrame(frame);
  }

  // Only spin while the figure is on screen.
  new IntersectionObserver((entries) => {
    const visible = entries.some((e) => e.isIntersecting);
    if (visible && !running) { running = true; requestAnimationFrame(frame); }
    if (!visible) running = false;
  }).observe(box);

  Promise.all(stages.map((s) => loadModel(s.dataset.src)))
    .then((geoms) => {
      // One scale for every model in the box, so sizes compare honestly.
      let biggest = 0;
      const size = new THREE.Vector3();
      for (const g of geoms) {
        g.boundingBox.getSize(size);
        biggest = Math.max(biggest, size.x, size.y, size.z);
      }
      const k = 2.6 / biggest;
      const c = new THREE.Vector3();
      geoms.forEach((g, i) => {
        g.boundingBox.getCenter(c);
        g.translate(-c.x, -c.y, -c.z);
        g.scale(k, k, k);
        panes[i].setMesh(g);
      });
      resetView();
      setAuto(true);
      box.classList.add("is-ready");
    })
    .catch((err) => {
      box.classList.add("has-error");
      console.error(err);
    });
}

// Load each figure when it's about to come into view.
const waiting = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (e.isIntersecting) {
      waiting.unobserve(e.target);
      setUp(e.target);
    }
  }
}, { rootMargin: "400px 0px" });
document.querySelectorAll(".model-compare").forEach((box) => waiting.observe(box));
