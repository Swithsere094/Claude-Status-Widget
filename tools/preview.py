"""Genera una pagina HTML con todas las mascotas animadas, para revisarlas en el navegador.

Uso:
    python tools/preview.py                 # crea preview.html en la raiz del proyecto
    python tools/preview.py -o otra.html

Solo incluye las mascotas que cumplen el contrato (ver tools/check_pets.py).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pet_contract import REQUIRED_STATES, load_pets  # noqa: E402

TEMPLATE = r"""<title>Mascotas de Claude Code</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@500;700&family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<style>
/* Layout: una columna; arriba el escritorio simulado, luego una seccion por mascota con su matriz colores x estados. Look oscuro unico, como el escritorio donde vive el widget. */
:root {
  color-scheme: dark;
  --desk: #171b22;
  --panel: #1f252e;
  --line: #2c3440;
  --ink: #e6ebf2;
  --muted: #8d98a8;
  --accent: #5fc4b6;
  --f-display: "Pixelify Sans", ui-monospace, "Cascadia Mono", monospace;
  --f-body: "Atkinson Hyperlegible", "Segoe UI", system-ui, sans-serif;
}
* { box-sizing: border-box; }
body {
  background: var(--desk); color: var(--ink);
  font-family: var(--f-body); font-size: 15px; line-height: 1.55;
  padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
}
main { max-width: 1000px; margin: 0 auto; display: grid; gap: 44px; }
h1, h2, h3 { font-family: var(--f-display); font-weight: 700; text-wrap: balance; margin: 0; }
h1 { font-size: 2rem; }
h2 { font-size: 1.15rem; letter-spacing: .02em; }
h3 { font-size: 1.5rem; }
p { margin: 0; max-width: 65ch; }
.lede, .muted { color: var(--muted); }
header, section { display: grid; gap: 12px; }
.desk {
  border: 1px solid var(--line); border-radius: 6px;
  background:
    linear-gradient(transparent 31px, rgba(255,255,255,.025) 32px) 0 0 / 100% 32px,
    linear-gradient(90deg, transparent 31px, rgba(255,255,255,.025) 32px) 0 0 / 32px 100%,
    var(--panel);
  min-height: 260px; padding: 18px;
  display: flex; justify-content: flex-end; align-items: flex-start; overflow: hidden;
}
.widget { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.slot { display: grid; justify-items: center; gap: 2px; }
canvas { image-rendering: pixelated; display: block; }
.pill {
  font-size: 11px; font-weight: 700; background: #0f1217; color: var(--ink);
  padding: 1px 8px; border-radius: 3px; max-width: 110px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.log { color: var(--muted); font-size: 13px; min-height: 1.5em; }
.pet-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.species { font-family: var(--f-display); color: var(--accent); font-size: .95rem; letter-spacing: .04em; text-transform: uppercase; }
.matrix-wrap { overflow-x: auto; }
table { border-collapse: collapse; }
th { font-family: var(--f-display); font-weight: 500; font-size: .8rem; color: var(--muted); letter-spacing: .04em; text-transform: uppercase; padding: 4px; }
th[scope="row"] { text-align: right; padding-right: 10px; text-transform: none; font-size: .9rem; white-space: nowrap; }
td { padding: 1px 3px; }
td button { background: none; border: 1px solid transparent; border-radius: 4px; padding: 2px; cursor: pointer; }
td button:hover { border-color: var(--line); }
td button:focus-visible { outline: none; border-color: var(--accent); }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
.hint { color: var(--muted); font-size: 13px; }
</style>

<main>
  <header>
    <h1>Mascotas de Claude Code</h1>
    <p class="lede">Las mascotas del widget, animadas con los mismos archivos que lee en Windows. Cada proyecto recibe al azar una mascota y uno de sus colores, y los conserva.</p>
  </header>

  <section aria-labelledby="sim-title">
    <h2 id="sim-title">Así se vería tu escritorio con 4 sesiones (×4)</h2>
    <div class="desk"><div class="widget" id="sim"></div></div>
    <p class="log" id="log" aria-live="polite"></p>
  </section>

  <div id="pets" style="display:grid;gap:44px"></div>
  <p class="hint">Haz clic en cualquier mascota de las matrices para repetir su animación desde el inicio.</p>
</main>

<script>
const PETS = __PETS_JSON__;
const STATES = __STATES_JSON__;
const W = 24, H = 24;

/* Orden de disolucion fijo por mascota (PRNG con semilla), igual en cada frame. */
function seeded(seed) { let s = 0; for (const c of seed) s = (s * 31 + c.charCodeAt(0)) >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const RANK = {};
for (const id in PETS) {
  const cells = []; for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) cells.push([x, y]);
  const r = seeded(id);
  for (let i = cells.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [cells[i], cells[j]] = [cells[j], cells[i]]; }
  const m = new Float32Array(W * H); cells.forEach(([x, y], i) => m[y * W + x] = i / cells.length); RANK[id] = m;
}

/* Cache de frames: un canvas 24x24 por combinacion; se escala al dibujar. */
const cache = new Map();
function frameCanvas(petId, pal, layers, dx, dy, dis) {
  const key = petId + "|" + pal + "|" + layers.join(",") + "|" + dx + "|" + dy + "|" + dis;
  let c = cache.get(key); if (c) return c;
  const pet = PETS[petId];
  const cols = Object.assign({}, pet.shared_colors, pet.palettes[pal]);
  const hidden = new Set(pet.palettes[pal].hide_layers || []);
  const fixed = new Set(pet.fixed_layers || []);
  c = document.createElement("canvas"); c.width = W; c.height = H;
  const ctx = c.getContext("2d");
  for (const name of layers) {
    if (hidden.has(name)) continue;
    const L = pet.layers[name], ox = fixed.has(name) ? 0 : dx, oy = fixed.has(name) ? 0 : dy;
    L.rows.forEach((row, y) => {
      for (let x = 0; x < row.length; x++) {
        const ch = row[x]; if (ch === pet.transparent) continue;
        const xx = L.x + x + ox, yy = L.y + y + oy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
        if (dis && RANK[petId][yy * W + xx] < dis) continue;
        ctx.fillStyle = cols[ch]; ctx.fillRect(xx, yy, 1, 1);
      }
    });
  }
  cache.set(key, c); return c;
}

class Pet {
  constructor(canvas, petId, pal, state, scale, replayBye) {
    this.c = canvas; this.ctx = canvas.getContext("2d"); this.ctx.imageSmoothingEnabled = false;
    canvas.width = W * scale; canvas.height = H * scale;
    this.pet = PETS[petId]; this.petId = petId; this.pal = pal; this.replayBye = replayBye;
    this.setState(state);
  }
  setState(state) {
    this.state = state; const a = this.pet.animations[state];
    this.queue = a.intro ? [...a.intro] : []; this.i = 0; this.elapsed = 0;
    this.blinkSeq = null; this.nextBlink = this.randBlink(); this.wait = 0;
  }
  randBlink() { const b = this.pet.blink; return b ? b.min_ms + Math.random() * (b.max_ms - b.min_ms) : 0; }
  current() { const a = this.pet.animations[this.state]; return this.queue.length ? this.queue[0] : a.loop[this.i % a.loop.length]; }
  tick(dt) {
    const a = this.pet.animations[this.state];
    if (a.end && !this.queue.length && this.replayBye) {  // en la vista previa la despedida se repite
      if ((this.wait += dt) > 900) this.setState(this.state);
      return;
    }
    this.elapsed += dt; let f = this.current();
    while (this.elapsed >= f.ms) { this.elapsed -= f.ms; if (this.queue.length) this.queue.shift(); else this.i++; f = this.current(); }
    if (a.blink && this.pet.blink && !this.queue.length) {
      if (this.blinkSeq) {
        this.blinkT += dt;
        while (this.blinkSeq.length && this.blinkT >= this.blinkSeq[0][1]) { this.blinkT -= this.blinkSeq[0][1]; this.blinkSeq.shift(); }
        if (!this.blinkSeq.length) { this.blinkSeq = null; this.nextBlink = this.randBlink(); }
      } else if ((this.nextBlink -= dt) <= 0) { this.blinkSeq = this.pet.blink.sequence.map(s => [...s]); this.blinkT = 0; }
    }
  }
  draw() {
    const f = this.current(), targets = this.blinkSeq ? this.pet.blink.targets : [];
    const layers = f.layers.map(n => targets.includes(n) ? this.blinkSeq[0][0] : n);
    this.ctx.clearRect(0, 0, this.c.width, this.c.height);
    this.ctx.drawImage(frameCanvas(this.petId, this.pal, layers, f.dx || 0, f.dy || 0, f.dissolve || 0), 0, 0, this.c.width, this.c.height);
  }
}

const all = [];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Secciones por mascota */
const petsEl = document.getElementById("pets");
for (const [id, pet] of Object.entries(PETS)) {
  const sec = document.createElement("section");
  sec.setAttribute("aria-label", pet.name);
  sec.innerHTML = `<div class="pet-head"><h3>${pet.name}</h3><span class="species">${pet.species || ""}</span></div><p class="muted">${pet.description || ""}</p>`;
  const wrap = document.createElement("div"); wrap.className = "matrix-wrap";
  const table = document.createElement("table");
  const head = table.insertRow(); head.appendChild(document.createElement("th"));
  STATES.forEach(s => { const th = document.createElement("th"); th.scope = "col"; th.textContent = pet.animations[s].label || s; head.appendChild(th); });
  for (const [pk, pal] of Object.entries(pet.palettes)) {
    const tr = table.insertRow(); const th = document.createElement("th"); th.scope = "row";
    th.innerHTML = `<span class="swatch" style="background:${pal.B || "#888"}"></span>${pal.name}`; tr.appendChild(th);
    STATES.forEach(s => {
      const td = tr.insertCell(); const b = document.createElement("button"); b.type = "button";
      b.setAttribute("aria-label", `${pet.name} ${pal.name}, ${pet.animations[s].label || s}`);
      const cv = document.createElement("canvas"); b.appendChild(cv); td.appendChild(b);
      const p = new Pet(cv, id, pk, s, 3, true); b.addEventListener("click", () => p.setState(s)); all.push(p);
    });
  }
  wrap.appendChild(table); sec.appendChild(wrap); petsEl.appendChild(sec);
}

/* Escritorio simulado: una sesion por mascota (hasta 4) */
const sim = document.getElementById("sim"), log = document.getElementById("log");
const PROJECTS = ["api-backend", "sitio-web", "scripts-datos", "app-movil"];
const ids = Object.keys(PETS);
const sessions = ids.slice(0, 4).map((id, i) => {
  const pals = Object.keys(PETS[id].palettes);
  const s = { project: PROJECTS[i], id, pal: pals[(i * 2) % pals.length] };
  const el = document.createElement("div"); el.className = "slot";
  const cv = document.createElement("canvas"); const pill = document.createElement("div"); pill.className = "pill"; pill.textContent = s.project;
  el.append(cv, pill); sim.appendChild(el);
  s.pet = new Pet(cv, id, s.pal, ["working", "idle", "waiting", "done"][i % 4], 4, true); all.push(s.pet);
  return s;
});
const NEXT = { idle: "working", working: "done", done: "idle", waiting: "working", sleep: "working", bye: "idle" };
function step() {
  const s = sessions[Math.floor(Math.random() * sessions.length)];
  let next = NEXT[s.pet.state] || "idle";
  if (s.pet.state === "working" && Math.random() < .35) next = "waiting";
  if (s.pet.state === "idle" && Math.random() < .15) next = "bye";
  s.pet.setState(next);
  log.textContent = `${s.project} (${PETS[s.id].name}): ${PETS[s.id].animations[next].label || next}`;
}
if (!reduce) setInterval(step, 3000);
log.textContent = "Ejemplo: los estados cambian solos cada pocos segundos.";

let last = performance.now();
function frame(now) {
  const dt = Math.min(now - last, 250); last = now;
  for (const p of all) { if (!reduce) p.tick(dt); p.draw(); }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", default=str(ROOT / "preview.html"))
    args = ap.parse_args()

    pets, problems = load_pets(ROOT / "pets")
    for folder, errors in problems.items():
        print(f"Se omite '{folder}': {errors[0]}" + (f" (y {len(errors) - 1} errores mas)" if len(errors) > 1 else ""))
    if not pets:
        raise SystemExit("No hay mascotas validas en pets/.")
    html = (TEMPLATE
            .replace("__PETS_JSON__", json.dumps(pets, ensure_ascii=False, separators=(",", ":")))
            .replace("__STATES_JSON__", json.dumps(list(REQUIRED_STATES))))
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Vista previa con {len(pets)} mascotas: {args.output}")


if __name__ == "__main__":
    main()
