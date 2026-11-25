// 3D anatomy viewer: one CT scan segmented into structures (skull, jaws,
// organs...) that readers can spin, zoom and slice, with a menu to switch
// each structure or whole system on and off, or fade it.
//
// Used from a page like this (see education/posts/anatomy-viewer-test.qmd):
//
//   <div class="anatomy-viewer"
//        data-organs="../../assets/models/scan-name/organs.csv"
//        aria-label="What the model shows"></div>
//   <script type="module" src="../../assets/js/anatomy-viewer.js"></script>
//
// The figure runs wider than the text column (see _rules.scss). The script
// builds everything inside the box: the 3D view, the menu under
// it, and the buttons. Which structures there are, and their labels, systems, colours and
// starting opacities, all come from organs.csv, which
// scripts/make_anatomy_model.py writes next to the models. Edit that file
// freely; the page picks up changes on reload. The box can also take
// data-start="x,y,z" for the starting view direction, as in model-viewer.js.
//
// The models are the same .bin format model-viewer.js uses, in the scan's
// own coordinates, so the parts line up as they were segmented. Nothing is
// downloaded until the figure is about to scroll into view.

import * as THREE from "./three/three.module.min.js";
import { OrbitControls } from "./three/OrbitControls.js";

// In the models, +y is dorsal (up) and +z is anterior (the snout).
const START_DIR = new THREE.Vector3(-0.55, 0.75, 0.9).normalize();
const START_DIST = 5.4;
const FIT = 2.6;            // the whole scan is scaled so its longest side is this
const PICK_MIN = 0.35;      // clicks pass through anything fainter than this
const FALLBACK = "#ddd3bd"; // colour for a row with no (or a broken) colour

// ---------------------------------------------------------------------------
// Reading organs.csv

function parseCSV(text) {
  text = text.replace(/^﻿/, "");
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += ch;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  const head = (rows.shift() || []).map((h) => h.trim().toLowerCase());
  return rows
    .filter((r) => r.some((c) => c.trim() !== ""))
    .map((r) => Object.fromEntries(head.map((h, i) => [h, (r[i] ?? "").trim()])));
}

function readOrgans(rows, base) {
  return rows.filter((r) => r.file).map((r) => {
    const hex = (r.color || "").replace(/^#?/, "#");
    const op = parseFloat(r.opacity);
    return {
      url: new URL(r.file, base).href,
      label: r.label || r.file.replace(/\.bin$/i, ""),
      system: r.system || "Other",
      color: /^#[0-9a-f]{6}$/i.test(hex) ? hex : FALLBACK,
      opacity: Number.isFinite(op) ? Math.min(100, Math.max(0, op)) / 100 : 1,
      show: !/^(no|n|false|0|off|hide|hidden)$/i.test(r.show || ""),
    };
  });
}

// Same as loadModel in model-viewer.js (see scripts/make_web_model.py for
// the file layout).
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

// ---------------------------------------------------------------------------
// Building the figure

function el(tag, cls, attrs = {}) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

let boxCount = 0;

async function setUp(box) {
  const id = `anat${++boxCount}`;

  // Layout: the 3D view as big as fits, the usual hint line, then the menu.
  const stage = el("div", "anatomy-stage", {
    role: "img",
    "aria-label": box.getAttribute("aria-label") || "Rotatable 3D model",
  });
  box.removeAttribute("aria-label");
  const status = el("div", "anatomy-status");
  status.textContent = "Loading 3D model…";
  const tag = el("div", "anatomy-tag", { "aria-live": "polite" });
  tag.hidden = true;
  stage.append(status, tag);
  const panel = el("div", "anatomy-panel");
  const bar = el("div", "model-bar");
  const hint = el("span", "model-hint");
  hint.textContent = matchMedia("(pointer: coarse)").matches
    ? "Drag to rotate, pinch to zoom, and use two fingers to move it. Tap a part to name it."
    : "Drag to rotate. Click, then scroll to zoom. Right-drag to move it. " +
      "Click a part to name it; double-click to turn around that spot.";
  bar.append(hint);
  const err = el("p", "model-error");
  err.textContent = "The 3D model needs a browser with WebGL turned on.";
  box.append(stage, bar, panel, err);

  // The 3D scene, lit like the skulls in model-viewer.js.
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (e) {
    box.classList.add("has-error");
    console.error(e);
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.localClippingEnabled = true;
  const canvas = renderer.domElement;
  stage.prepend(canvas);

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

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enableZoom = false; // switched on once the reader grabs the model
  controls.minDistance = 0.4;
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

  // Load the list of parts, then every model.
  let organs;
  try {
    const csvUrl = new URL(box.dataset.organs, location.href);
    const res = await fetch(csvUrl);
    if (!res.ok) throw new Error(`${csvUrl}: HTTP ${res.status}`);
    organs = readOrgans(parseCSV(await res.text()), csvUrl);
    if (!organs.length) throw new Error(`${csvUrl} lists no models`);
    let loaded = 0;
    const geoms = await Promise.all(organs.map((o) => loadModel(o.url).then((g) => {
      status.textContent = `Loading 3D model… ${++loaded} of ${organs.length}`;
      return g;
    })));
    organs.forEach((o, i) => { o.geom = geoms[i]; });
  } catch (e) {
    box.classList.add("has-error");
    console.error(e);
    return;
  }

  // One centre and one scale for the whole scan, so the parts stay where
  // they were segmented relative to each other.
  const bounds = new THREE.Box3();
  for (const o of organs) bounds.union(o.geom.boundingBox);
  const centre = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const k = FIT / Math.max(size.x, size.y, size.z);
  for (const o of organs) {
    o.geom.translate(-centre.x, -centre.y, -centre.z);
    o.geom.scale(k, k, k);
    o.geom.computeBoundingBox();
    o.geom.computeBoundingSphere();
  }
  bounds.translate(centre.clone().negate());
  bounds.min.multiplyScalar(k);
  bounds.max.multiplyScalar(k);

  // Each part is a mesh, plus a flat, darker copy of its inside that only
  // shows when the model is sliced, so cut surfaces read as solid.
  const clipPlane = new THREE.Plane(new THREE.Vector3(0, 0, -1), 0);
  let slicing = false;
  for (const o of organs) {
    const color = new THREE.Color(o.color);
    o.mat = new THREE.MeshStandardMaterial({ color, roughness: 0.62, metalness: 0 });
    o.mesh = new THREE.Mesh(o.geom, o.mat);
    o.capMat = new THREE.MeshBasicMaterial({ color: color.clone().multiplyScalar(0.45), side: THREE.BackSide });
    o.cap = new THREE.Mesh(o.geom, o.capMat);
    o.mesh.userData.organ = o.cap.userData.organ = o;
    o.start = { show: o.show, opacity: o.opacity };
    scene.add(o.mesh, o.cap);
  }
  // See-through parts are drawn biggest first, so a faded outer layer (skin,
  // skull) doesn't hide what's inside it.
  [...organs]
    .sort((a, b) => b.geom.boundingSphere.radius - a.geom.boundingSphere.radius)
    .forEach((o, i) => { o.mesh.renderOrder = i; o.cap.renderOrder = i; });

  let hovered = null, picked = null;
  function glow() {
    for (const o of organs) {
      const g = o === hovered ? 0.5 : o === picked ? 0.2 : 0;
      o.mat.emissive.copy(o.mat.color).multiplyScalar(g);
    }
  }

  function apply(o) {
    const on = o.show && o.opacity > 0.004;
    const solid = o.opacity >= 0.996;
    o.mesh.visible = on;
    o.mat.opacity = o.opacity;
    if (o.mat.transparent === solid) {
      o.mat.transparent = !solid;
      o.mat.depthWrite = solid;
      o.mat.needsUpdate = true;
    }
    o.cap.visible = on && solid && slicing;
    o.check.checked = o.show;
    o.range.value = Math.round(o.opacity * 100);
    o.row.classList.toggle("is-off", !on);
  }

  // --- The menu ------------------------------------------------------------
  const systems = new Map();
  for (const o of organs) {
    if (!systems.has(o.system)) systems.set(o.system, []);
    systems.get(o.system).push(o);
  }
  const list = el("div", "anatomy-systems");
  const syncs = [];
  let n = 0;

  for (const [name, members] of systems) {
    const sys = el("section", "anatomy-system");
    const head = el("div", "anatomy-system-head");
    const sc = el("input", "", { type: "checkbox", id: `${id}-s${n}` });
    const sl = el("label", "", { for: sc.id });
    sl.textContent = name;
    head.append(sc, sl);
    if (systems.size > 1) {
      const only = el("button", "anatomy-only", { type: "button", title: `Show only ${name}` });
      only.textContent = "only";
      only.addEventListener("click", () => {
        for (const o of organs) {
          o.show = o.system === name;
          if (o.show && o.opacity < 0.05) o.opacity = o.start.opacity || 1;
          apply(o);
        }
        syncAll();
        quiet();
      });
      head.append(only);
    }
    const fold = el("button", "anatomy-fold", { type: "button", "aria-expanded": "true", "aria-label": `Hide the list for ${name}` });
    head.append(fold);
    const ul = el("ul", "anatomy-organs");
    fold.addEventListener("click", () => {
      const open = ul.hidden;
      ul.hidden = !open;
      fold.setAttribute("aria-expanded", String(open));
      fold.setAttribute("aria-label", `${open ? "Hide" : "Show"} the list for ${name}`);
    });

    for (const o of members) {
      const li = el("li", "anatomy-organ");
      const c = el("input", "", { type: "checkbox", id: `${id}-o${n++}` });
      const sw = el("span", "anatomy-swatch", { "aria-hidden": "true" });
      sw.style.background = o.color;
      const lab = el("label", "", { for: c.id });
      lab.textContent = o.label;
      const r = el("input", "", { type: "range", min: "0", max: "100", step: "1", "aria-label": `Opacity of ${o.label}` });
      li.append(c, sw, lab, r);
      c.addEventListener("change", () => {
        o.show = c.checked;
        if (o.show && o.opacity < 0.05) o.opacity = o.start.opacity || 1;
        apply(o); syncAll(); quiet();
      });
      r.addEventListener("input", () => {
        o.opacity = r.value / 100;
        o.show = o.opacity > 0;
        apply(o); syncAll(); quiet();
      });
      li.addEventListener("pointerenter", () => { hovered = o; glow(); });
      li.addEventListener("pointerleave", () => { if (hovered === o) hovered = null; glow(); });
      Object.assign(o, { row: li, check: c, range: r });
      ul.append(li);
    }

    sc.addEventListener("change", () => {
      for (const o of members) {
        o.show = sc.checked;
        if (o.show && o.opacity < 0.05) o.opacity = o.start.opacity || 1;
        apply(o);
      }
      syncAll(); quiet();
    });
    syncs.push(() => {
      const on = members.filter((o) => o.show).length;
      sc.checked = on === members.length;
      sc.indeterminate = on > 0 && on < members.length;
    });
    sys.append(head, ul);
    list.append(sys);
  }
  function syncAll() { syncs.forEach((f) => f()); }

  // Slicing: a plane that cuts away part of the model, moved with a slider.
  const slice = el("div", "anatomy-slice");
  const sel = el("select", "", { id: `${id}-cut` });
  for (const [v, t] of [["", "Off"], ["z", "Transverse (front to back)"],
    ["x", "Sagittal (side to side)"], ["y", "Frontal (top down)"]]) {
    const opt = el("option", "", { value: v });
    opt.textContent = t;
    sel.append(opt);
  }
  const sliceLab = el("label", "", { for: sel.id });
  sliceLab.textContent = "Slice";
  const cut = el("input", "", { type: "range", min: "0", max: "100", value: "50", step: "0.5", "aria-label": "How much to slice away", disabled: "" });
  slice.append(sliceLab, sel, cut);

  function setSlice() {
    const axis = sel.value;
    const was = slicing;
    slicing = axis !== "";
    cut.disabled = !slicing;
    if (slicing) {
      // The slider says how much is cut away: none at 0, all of it at 100.
      const lo = bounds.min[axis] - 0.01, hi = bounds.max[axis] + 0.01;
      clipPlane.normal.set(0, 0, 0);
      clipPlane.normal[axis] = -1;
      clipPlane.constant = hi - (cut.value / 100) * (hi - lo);
    }
    if (was !== slicing) {
      for (const o of organs) {
        for (const m of [o.mat, o.capMat]) {
          m.clippingPlanes = slicing ? [clipPlane] : null;
          m.needsUpdate = true;
        }
      }
    }
    organs.forEach(apply);
  }
  sel.addEventListener("change", () => { setSlice(); quiet(); });
  cut.addEventListener("input", () => { setSlice(); quiet(); });

  const buttons = el("div", "anatomy-buttons");
  const resetBtn = el("button", "model-reset", { type: "button" });
  resetBtn.textContent = "Reset";
  buttons.append(resetBtn);
  if (document.fullscreenEnabled && box.requestFullscreen) {
    const fsBtn = el("button", "model-reset", { type: "button" });
    fsBtn.textContent = "Full screen";
    fsBtn.addEventListener("click", () => {
      if (document.fullscreenElement === box) document.exitFullscreen();
      else box.requestFullscreen().catch((e) => console.error(e));
    });
    document.addEventListener("fullscreenchange", () => {
      const full = document.fullscreenElement === box;
      box.classList.toggle("is-full", full);
      fsBtn.textContent = full ? "Exit full screen" : "Full screen";
    });
    buttons.append(fsBtn);
  }
  const tools = el("div", "anatomy-tools");
  tools.append(slice, buttons);
  panel.append(list, tools);

  // --- Clicking parts in the model ------------------------------------------
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function pick(ev) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const targets = [];
    for (const o of organs) {
      if (!o.mesh.visible || o.opacity < PICK_MIN) continue;
      targets.push(o.mesh);
      if (o.cap.visible) targets.push(o.cap); // the cut face, when sliced
    }
    for (const hit of ray.intersectObjects(targets, false)) {
      if (slicing && clipPlane.distanceToPoint(hit.point) < -1e-4) continue;
      return hit;
    }
    return null;
  }
  function setPicked(o) {
    picked = o;
    for (const p of organs) p.row.classList.toggle("is-picked", p === o);
    if (o) {
      tag.innerHTML = "";
      const b = el("strong");
      b.textContent = o.label;
      const s = el("span");
      s.textContent = o.system;
      tag.append(b, s);
      tag.hidden = false;
      // In full screen the menu can scroll, so bring its row into view.
      // (On the page the whole menu shows, and the page stays put.)
      if (document.fullscreenElement === box) o.row.scrollIntoView({ block: "nearest" });
    } else tag.hidden = true;
    glow();
  }
  let down = null;
  canvas.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  canvas.addEventListener("pointerup", (e) => {
    if (!down) return;
    const still = Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6;
    const quick = performance.now() - down.t < 500;
    down = null;
    if (still && quick) {
      const hit = pick(e);
      setPicked(hit ? hit.object.userData.organ : null);
    }
  });
  let goal = null; // where the view is gliding to after a double-click
  canvas.addEventListener("dblclick", (e) => {
    const hit = pick(e);
    if (hit) { goal = hit.point.clone(); setAuto(false); }
  });

  // --- View, reset and animation ---------------------------------------------
  const startDir = START_DIR.clone();
  if (box.dataset.start) {
    const v = box.dataset.start.split(",").map(Number);
    if (v.length === 3 && v.every(Number.isFinite)) startDir.set(v[0], v[1], v[2]).normalize();
  }
  function resetView() {
    goal = null;
    controls.target.set(0, 0, 0);
    camera.position.copy(startDir).multiplyScalar(START_DIST);
    camera.up.set(0, 1, 0);
    controls.update();
  }
  function setAuto(on) { controls.autoRotate = on; }
  function quiet() { setAuto(false); } // stop spinning once the reader takes over
  controls.addEventListener("start", () => { goal = null; setAuto(false); });

  resetBtn.addEventListener("click", () => {
    for (const o of organs) { o.show = o.start.show; o.opacity = o.start.opacity; }
    sel.value = "";
    cut.value = 50;
    setSlice();
    syncAll();
    setPicked(null);
    resetView();
    setAuto(true);
  });

  // Wheel-zoom only after the reader has grabbed the model, so scrolling down
  // the page past the figure doesn't get caught by it. Pinch works right away.
  stage.addEventListener("pointerdown", () => { controls.enableZoom = true; });
  stage.addEventListener("pointerleave", (e) => {
    if (e.pointerType === "mouse" && !box.classList.contains("is-full")) controls.enableZoom = false;
  });
  stage.addEventListener("touchstart", () => { controls.enableZoom = true; }, { passive: true });

  let running = false;
  function frame() {
    if (!running) return;
    if (goal) {
      controls.target.lerp(goal, 0.16);
      if (controls.target.distanceToSquared(goal) < 1e-8) goal = null;
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  // Only draw while the figure is on screen.
  new IntersectionObserver((entries) => {
    const visible = entries.some((e) => e.isIntersecting);
    if (visible && !running) { running = true; requestAnimationFrame(frame); }
    if (!visible) running = false;
  }).observe(box);

  setSlice();
  syncAll();
  resetView();
  setAuto(true);
  box.classList.add("is-ready");
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
document.querySelectorAll(".anatomy-viewer").forEach((box) => waiting.observe(box));
