"""Widget flotante con una mascota animada por cada sesion de Claude Code.

- Arrastrar con clic izquierdo para moverlo.
- Doble clic sobre una mascota para descartar esa sesion.
- Clic derecho para cerrar el widget (se vuelve a abrir con la proxima sesion).
- Se cierra solo cuando no queda ninguna sesion de Claude Code abierta.

Las mascotas se leen de pets/<id>/pet.json (ver pet_contract.py).
Cada proyecto recibe al azar una mascota y un color, y los conserva.
Requiere: pip install psutil
"""
import json
import random
import socket
import sys
import time
import tkinter as tk
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pet_contract import HEIGHT, WIDTH, load_pets, palette_colors  # noqa: E402

try:
    import winsound
except ImportError:  # fuera de Windows (pruebas)
    winsound = None

# ---------------------------------------------------------------- ajustes
PETS_DIR = HERE / "pets"
CLAUDE_DIR = Path.home() / ".claude"
STATUS_DIR = CLAUDE_DIR / "status"
REGISTRY_FILE = CLAUDE_DIR / "claude_widget_pets.json"
LEGACY_COLORS_FILE = CLAUDE_DIR / "claude_widget_colors.json"  # registro de la version de solo buhos
LEGACY_PET = "bubo"
LOG_FILE = CLAUDE_DIR / "claude_widget.log"

SCALE = 4                  # entero, para que el pixel art se vea nitido
SLEEP_AFTER = 10 * 60      # segundos inactiva o lista antes de dormirse
STALE_SECONDS = 6 * 3600   # respaldo si no se pudo identificar el proceso
EMPTY_CLOSE_SECONDS = 5    # se cierra tras 5 s sin sesiones
FRAME_MS = 33              # ~30 fps
POLL_MS = 1000             # lectura de estados
GAP = 6                    # separacion entre mascotas (px)
PILL_H = 16
MARGIN = 40                # distancia inicial al borde superior derecho
KEY = "#ff00fe"            # color que Windows vuelve transparente
PILL_BG = "#0f1217"
PILL_FG = "#e6ebf2"
FONT = ("Segoe UI", 9, "bold")
SOUND_STATES = {"done": "MB_ICONASTERISK", "waiting": "MB_ICONEXCLAMATION"}


def log(msg):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except OSError:
        pass


# ---------------------------------------------------------------- sesiones
def session_alive(d):
    """True si el proceso de Claude Code de esa sesion sigue vivo."""
    if "pid" not in d:              # archivo de una version anterior
        return False
    pid = d["pid"]
    if pid is None:                 # no se identifico el proceso: usar caducidad
        return time.time() - d.get("ts", 0) < STALE_SECONDS
    try:
        # Comparar la hora de creacion evita confundirse si Windows reutiliza el PID.
        return abs(psutil.Process(pid).create_time() - (d.get("pid_ctime") or 0)) < 1
    except psutil.Error:
        return False


def load_sessions():
    sessions = {}
    for f in STATUS_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not session_alive(d):
            f.unlink(missing_ok=True)
            continue
        sessions[f.stem] = d
    return sessions


# ---------------------------------------------------------------- asignacion
class PetRegistry:
    """Asigna a cada proyecto una mascota y un color al azar, y los recuerda."""

    def __init__(self, pets):
        self.pets = pets
        self.map = self._load()

    def _load(self):
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        # Migracion: los proyectos de la version anterior conservan su buho y su color.
        try:
            old = json.loads(LEGACY_COLORS_FILE.read_text(encoding="utf-8"))
            migrated = {project: {"pet": LEGACY_PET, "color": color} for project, color in old.items()}
            self._save(migrated)
            return migrated
        except Exception:
            return {}

    def _save(self, data=None):
        try:
            REGISTRY_FILE.write_text(json.dumps(data if data is not None else self.map,
                                                indent=1, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def _valid(self, entry):
        return (isinstance(entry, dict) and entry.get("pet") in self.pets
                and entry.get("color") in self.pets[entry["pet"]]["palettes"])

    def assign(self, project, on_screen, forced_pet=None, persist=True):
        """Mascota y color para un proyecto.

        on_screen: combinaciones (mascota, color) que ya estan en pantalla, para no repetirlas.
        forced_pet: obliga a usar esa mascota (lo usa el simulador).
        persist: False para sesiones simuladas, que nunca se guardan en el registro.
        """
        entry = self.map.get(project)
        if persist and not forced_pet and self._valid(entry):
            return entry["pet"], entry["color"]

        on_screen = set(on_screen)
        pets_on_screen = {p for p, _ in on_screen}
        all_combos = [(p, c) for p, pet in self.pets.items() for c in pet["palettes"]
                      if forced_pet in (None, p)] or \
                     [(p, c) for p, pet in self.pets.items() for c in pet["palettes"]]
        free = [x for x in all_combos if x not in on_screen]
        # Primero, una mascota que no este en pantalla; si todas lo estan, una combinacion libre.
        candidates = [x for x in free if x[0] not in pets_on_screen] or free or all_combos
        pet_id = random.choice(sorted({p for p, _ in candidates}))
        color = random.choice([c for p, c in candidates if p == pet_id])

        if persist:
            self.map[project] = {"pet": pet_id, "color": color}
            self._save()
        return pet_id, color


# ---------------------------------------------------------------- animacion
class PetAnimation:
    """Maquina de estados de una mascota: intro, bucle y parpadeo aleatorio."""

    def __init__(self, pet, state):
        self.pet = pet
        self.set_state(state)

    def set_state(self, state):
        if state not in self.pet["animations"]:
            state = "idle"
        self.state = state
        self.queue = list(self.pet["animations"][state].get("intro", []))
        self.i = 0
        self.elapsed = 0
        self.blink_seq = None
        self.next_blink = self._rand_blink()

    def _rand_blink(self):
        b = self.pet.get("blink")
        return random.uniform(b["min_ms"], b["max_ms"]) if b else 0

    def _current(self):
        loop = self.pet["animations"][self.state]["loop"]
        return self.queue[0] if self.queue else loop[self.i % len(loop)]

    def tick(self, dt):
        anim = self.pet["animations"][self.state]
        self.elapsed += dt
        f = self._current()
        while self.elapsed >= f["ms"]:
            self.elapsed -= f["ms"]
            if self.queue:
                self.queue.pop(0)
            else:
                self.i += 1
            f = self._current()
        if anim.get("blink") and self.pet.get("blink") and not self.queue:
            if self.blink_seq:
                self.blink_t += dt
                while self.blink_seq and self.blink_t >= self.blink_seq[0][1]:
                    self.blink_t -= self.blink_seq[0][1]
                    self.blink_seq.pop(0)
                if not self.blink_seq:
                    self.blink_seq = None
                    self.next_blink = self._rand_blink()
            else:
                self.next_blink -= dt
                if self.next_blink <= 0:
                    self.blink_seq = [list(x) for x in self.pet["blink"]["sequence"]]
                    self.blink_t = 0

    def finished(self):
        """True cuando termino una animacion de salida (como la despedida)."""
        return self.pet["animations"][self.state].get("end", False) and not self.queue

    def frame_key(self):
        """(capas, dx, dy, dissolve) del frame actual, con el parpadeo aplicado."""
        f = self._current()
        targets = self.pet["blink"]["targets"] if self.blink_seq else ()
        layers = tuple(self.blink_seq[0][0] if n in targets else n for n in f["layers"])
        return layers, f.get("dx", 0), f.get("dy", 0), f.get("dissolve", 0)


class SpriteRenderer:
    """Convierte frames en PhotoImage escaladas y las guarda en cache."""

    def __init__(self, pets, scale):
        self.pets = pets
        self.scale = scale
        self.cache = {}
        self.dissolve_rank = {}
        for pid in pets:  # orden fijo de borrado por mascota, para que la disolucion no parpadee
            cells = [(x, y) for y in range(HEIGHT) for x in range(WIDTH)]
            random.Random(pid).shuffle(cells)
            self.dissolve_rank[pid] = {c: i / len(cells) for i, c in enumerate(cells)}

    def image(self, pet_id, palette, layers, dx, dy, dissolve):
        key = (pet_id, palette, layers, dx, dy, dissolve)
        img = self.cache.get(key)
        if img is None:
            img = self._render(*key)
            self.cache[key] = img
        return img

    def _render(self, pet_id, palette, layers, dx, dy, dissolve):
        pet = self.pets[pet_id]
        pal = pet["palettes"][palette]
        colors = dict(pet["shared_colors"])
        colors.update(palette_colors(pal))
        hidden = set(pal.get("hide_layers", []))
        fixed = set(pet.get("fixed_layers", []))
        grid = [[KEY] * WIDTH for _ in range(HEIGHT)]
        for name in layers:
            if name in hidden:
                continue
            L = pet["layers"][name]
            ox, oy = (0, 0) if name in fixed else (dx, dy)
            for y, row in enumerate(L["rows"]):
                yy = L["y"] + y + oy
                if not 0 <= yy < HEIGHT:
                    continue
                for x, ch in enumerate(row):
                    xx = L["x"] + x + ox
                    if ch != pet["transparent"] and 0 <= xx < WIDTH:
                        grid[yy][xx] = colors[ch]
        if dissolve:
            rank = self.dissolve_rank[pet_id]
            for (x, y), r in rank.items():
                if r < dissolve:
                    grid[y][x] = KEY
        base = tk.PhotoImage(width=WIDTH, height=HEIGHT)
        base.put(" ".join("{" + " ".join(r) + "}" for r in grid))
        return base.zoom(self.scale, self.scale)


# ---------------------------------------------------------------- widget
class Widget:
    def __init__(self, pets):
        self.pets = pets
        self.scale = SCALE
        self.pet_w = WIDTH * SCALE
        self.pet_h = HEIGHT * SCALE

        self.root = tk.Tk()
        r = self.root
        r.title("Mascotas de Claude Code")
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.configure(bg=KEY)
        if sys.platform == "win32":
            r.attributes("-transparentcolor", KEY)

        self.canvas = tk.Canvas(r, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.renderer = SpriteRenderer(pets, self.scale)
        self.registry = PetRegistry(pets)

        self.slots = {}         # session_id -> dict(anim, pet, palette, project, state, ...)
        self.order = []         # orden estable de izquierda a derecha
        self.empty_since = None
        self.right_edge = r.winfo_screenwidth() - MARGIN
        self.top = MARGIN
        self.last_tick = time.perf_counter()

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<Double-Button-1>", self._dismiss)
        self.canvas.bind("<Button-3>", lambda e: r.destroy())

        STATUS_DIR.mkdir(parents=True, exist_ok=True)
        self.poll()
        self.animate()

    # --- arrastre: se recuerda el borde derecho para que crezca hacia la izquierda
    def _start_drag(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def _drag(self, e):
        x, y = e.x_root - self._dx, e.y_root - self._dy
        self.root.geometry(f"+{x}+{y}")
        self.right_edge = x + self.canvas.winfo_width()
        self.top = y

    def _dismiss(self, e):
        idx = int(e.x // (self.pet_w + GAP))
        if 0 <= idx < len(self.order):
            (STATUS_DIR / f"{self.order[idx]}.json").unlink(missing_ok=True)

    # --- estados
    def effective_state(self, d):
        state = d.get("state", "idle")
        if state in ("idle", "done") and time.time() - d.get("ts", time.time()) > SLEEP_AFTER:
            return "sleep"
        return state

    def poll(self):
        sessions = load_sessions()
        # El widget se cierra cuando no hay sesiones ni mascotas despidiendose.
        if not sessions and not self.slots:
            self.empty_since = self.empty_since or time.time()
            if time.time() - self.empty_since > EMPTY_CLOSE_SECONDS:
                self.root.destroy()
                return
        else:
            self.empty_since = None

        changed_layout = False

        # Sesion cerrada: la mascota se despide; se retira cuando termina la animacion.
        for sid, slot in self.slots.items():
            if sid not in sessions and not slot.get("leaving"):
                slot["leaving"] = True
                slot["anim"].set_state("bye")

        for sid, d in sessions.items():
            state = self.effective_state(d)
            slot = self.slots.get(sid)
            if slot is not None and slot.get("leaving"):
                continue  # termina de despedirse; si la sesion sigue, vuelve en el siguiente ciclo
            if slot is None:
                project = d.get("project", "?")
                on_screen = [(s["pet"], s["palette"]) for s in self.slots.values() if not s.get("leaving")]
                simulated = bool(d.get("simulated"))
                pet_id, palette = self.registry.assign(project, on_screen,
                                                       forced_pet=d.get("pet") if simulated else None,
                                                       persist=not simulated)
                self.slots[sid] = {"anim": PetAnimation(self.pets[pet_id], state), "pet": pet_id,
                                   "palette": palette, "project": project, "state": state}
                self.order.append(sid)
                changed_layout = True
            elif slot["state"] != state:
                if state in SOUND_STATES and winsound:
                    winsound.MessageBeep(getattr(winsound, SOUND_STATES[state]))
                slot["anim"].set_state(state)
                slot["state"] = state

        if changed_layout:
            self.layout()
        self.root.after(POLL_MS, self.poll)

    # --- dibujo
    def _image_for(self, slot):
        layers, dx, dy, dissolve = slot["anim"].frame_key()
        return self.renderer.image(slot["pet"], slot["palette"], layers, dx, dy, dissolve)

    def layout(self):
        self.canvas.delete("all")
        n = max(len(self.order), 1)
        width = n * self.pet_w + (n - 1) * GAP
        height = self.pet_h + 2 + PILL_H
        self.canvas.config(width=width, height=height)
        self.root.geometry(f"{width}x{height}+{self.right_edge - width}+{self.top}")

        if not self.order:
            self._pill(width / 2, self.pet_h + 2, "sin agentes", "empty")
        for idx, sid in enumerate(self.order):
            slot = self.slots[sid]
            x = idx * (self.pet_w + GAP)
            tag = f"pet-{sid}"
            slot["image_item"] = self.canvas.create_image(x, 0, anchor="nw",
                                                          image=self._image_for(slot), tags=tag)
            self._pill(x + self.pet_w / 2, self.pet_h + 2, slot["project"], tag)

    def _pill(self, cx, top, text, tag):
        max_chars = max(4, self.pet_w // 7)
        label = text if len(text) <= max_chars else text[:max_chars - 1] + "…"
        t = self.canvas.create_text(cx, top + PILL_H / 2, text=label, fill=PILL_FG, font=FONT, tags=tag)
        x0, y0, x1, y1 = self.canvas.bbox(t)
        rect = self.canvas.create_rectangle(x0 - 6, top, x1 + 6, top + PILL_H,
                                            fill=PILL_BG, outline=PILL_BG, tags=tag)
        self.canvas.tag_lower(rect, t)

    def animate(self):
        now = time.perf_counter()
        dt = min((now - self.last_tick) * 1000, 250)
        self.last_tick = now
        gone = []
        for sid, slot in self.slots.items():
            slot["anim"].tick(dt)
            if slot.get("leaving") and slot["anim"].finished():
                gone.append(sid)
                continue
            if "image_item" in slot:
                self.canvas.itemconfig(slot["image_item"], image=self._image_for(slot))
        if gone:
            for sid in gone:
                del self.slots[sid]
                self.order.remove(sid)
            self.layout()
        self.root.after(FRAME_MS, self.animate)


def main():
    # Instancia unica: si el puerto ya esta tomado, otro widget esta abierto.
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", 47823))
    except OSError:
        raise SystemExit(0)

    pets, problems = load_pets(PETS_DIR)
    for folder, errors in problems.items():
        log(f"mascota '{folder}' ignorada: " + "; ".join(errors))
    if not pets:
        log(f"no hay mascotas validas en {PETS_DIR}; el widget no se abre")
        raise SystemExit(1)
    Widget(pets).root.mainloop()


if __name__ == "__main__":
    main()
