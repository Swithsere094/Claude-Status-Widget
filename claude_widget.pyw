"""Widget flotante con un buho animado por cada sesion de Claude Code.

- Arrastrar con clic izquierdo para moverlo.
- Doble clic sobre un buho para descartar esa sesion.
- Clic derecho para cerrar el widget (se vuelve a abrir con la proxima sesion).
- Se cierra solo cuando no queda ninguna sesion de Claude Code abierta.

Los sprites y animaciones se leen de sprites/owl.json.
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

try:
    import winsound
except ImportError:  # fuera de Windows (pruebas)
    winsound = None

# ---------------------------------------------------------------- ajustes
HERE = Path(__file__).resolve().parent
SPRITES_FILE = HERE / "sprites" / "owl.json"
STATUS_DIR = Path.home() / ".claude" / "status"
COLORS_FILE = Path.home() / ".claude" / "claude_widget_colors.json"

SCALE = None               # None = usar la escala de owl.json (entera, para pixel art nitido)
SLEEP_AFTER = 10 * 60      # segundos inactivo o listo antes de dormirse
STALE_SECONDS = 6 * 3600   # respaldo si no se pudo identificar el proceso
EMPTY_CLOSE_SECONDS = 5    # se cierra tras 5 s sin sesiones
FRAME_MS = 33              # ~30 fps
POLL_MS = 1000             # lectura de estados
GAP = 6                    # separacion entre buhos (px)
PILL_H = 16
MARGIN = 40                # distancia inicial al borde superior derecho
KEY = "#ff00fe"            # color que Windows vuelve transparente
PILL_BG = "#0f1217"
PILL_FG = "#e6ebf2"
FONT = ("Segoe UI", 9, "bold")
SOUND_STATES = {"done": "MB_ICONASTERISK", "waiting": "MB_ICONEXCLAMATION"}


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


# ---------------------------------------------------------------- colores
class ColorRegistry:
    """Asigna a cada proyecto un color fijo y lo recuerda entre ejecuciones."""

    def __init__(self, palettes):
        self.palettes = list(palettes)
        try:
            self.map = json.loads(COLORS_FILE.read_text(encoding="utf-8"))
        except Exception:
            self.map = {}

    def color_for(self, project, active_projects):
        if project in self.map and self.map[project] in self.palettes:
            return self.map[project]
        in_use = {self.map[p] for p in active_projects if p in self.map}
        free = [p for p in self.palettes if p not in in_use]
        if free:
            choice = free[0]
        else:  # todos ocupados: el menos repetido en el historial
            counts = {p: list(self.map.values()).count(p) for p in self.palettes}
            choice = min(self.palettes, key=lambda p: counts[p])
        self.map[project] = choice
        try:
            COLORS_FILE.write_text(json.dumps(self.map, indent=1, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return choice


# ---------------------------------------------------------------- animacion
class OwlAnimation:
    """Maquina de estados de un buho: intro, bucle y parpadeo aleatorio."""

    def __init__(self, sprites, state):
        self.s = sprites
        self.set_state(state)

    def set_state(self, state):
        if state not in self.s["animations"]:
            state = "idle"
        self.state = state
        anim = self.s["animations"][state]
        self.queue = list(anim.get("intro", []))
        self.i = 0
        self.elapsed = 0
        self.blink_seq = None
        self.next_blink = self._rand_blink()

    def _rand_blink(self):
        b = self.s["blink"]
        return random.uniform(b["min_ms"], b["max_ms"])

    def _current(self):
        loop = self.s["animations"][self.state]["loop"]
        return self.queue[0] if self.queue else loop[self.i % len(loop)]

    def tick(self, dt):
        anim = self.s["animations"][self.state]
        self.elapsed += dt
        f = self._current()
        while self.elapsed >= f["ms"]:
            self.elapsed -= f["ms"]
            if self.queue:
                self.queue.pop(0)
            else:
                self.i += 1
            f = self._current()
        if anim.get("blink") and not self.queue:
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
                    self.blink_seq = [list(x) for x in self.s["blink"]["sequence"]]
                    self.blink_t = 0

    def finished(self):
        """True cuando termino una animacion de salida (como la despedida)."""
        return self.s["animations"][self.state].get("end", False) and not self.queue

    def frame_key(self):
        """(capas, desplazamiento vertical) del frame actual, con el parpadeo aplicado."""
        f = self._current()
        targets = self.s["blink"]["targets"]
        layers = tuple(self.blink_seq[0][0] if (self.blink_seq and n in targets) else n
                       for n in f["layers"])
        return layers, f.get("dy", 0)


class SpriteRenderer:
    """Convierte frames en PhotoImage escaladas y las guarda en cache."""

    def __init__(self, sprites, scale):
        self.s = sprites
        self.scale = scale
        self.cache = {}

    def image(self, palette, layers, dy):
        key = (palette, layers, dy)
        img = self.cache.get(key)
        if img is None:
            img = self._render(palette, layers, dy)
            self.cache[key] = img
        return img

    def _render(self, palette, layers, dy):
        s = self.s
        w, h = s["width"], s["height"]
        colors = dict(s["shared_colors"])
        colors.update({k: v for k, v in s["palettes"][palette].items() if k != "name"})
        grid = [[KEY] * w for _ in range(h)]
        for name in layers:
            L = s["layers"][name]
            off = 0 if name in s["fixed_layers"] else dy
            for y, row in enumerate(L["rows"]):
                yy = L["y"] + y + off
                if not 0 <= yy < h:
                    continue
                for x, ch in enumerate(row):
                    if ch != s["transparent"]:
                        grid[yy][L["x"] + x] = colors[ch]
        base = tk.PhotoImage(width=w, height=h)
        base.put(" ".join("{" + " ".join(r) + "}" for r in grid))
        return base.zoom(self.scale, self.scale)


# ---------------------------------------------------------------- widget
class Widget:
    def __init__(self):
        self.sprites = json.loads(SPRITES_FILE.read_text(encoding="utf-8"))
        self.scale = int(SCALE or self.sprites.get("scale", 4))
        self.owl_w = self.sprites["width"] * self.scale
        self.owl_h = self.sprites["height"] * self.scale

        self.root = tk.Tk()
        r = self.root
        r.title("Buhos de Claude Code")
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.configure(bg=KEY)
        if sys.platform == "win32":
            r.attributes("-transparentcolor", KEY)

        self.canvas = tk.Canvas(r, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.renderer = SpriteRenderer(self.sprites, self.scale)
        self.colors = ColorRegistry(self.sprites["palettes"])

        self.owls = {}          # session_id -> dict(anim, palette, project, state, items)
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
        idx = int(e.x // (self.owl_w + GAP))
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
        # El widget se cierra cuando no hay sesiones ni buhos despidiendose.
        if not sessions and not self.owls:
            self.empty_since = self.empty_since or time.time()
            if time.time() - self.empty_since > EMPTY_CLOSE_SECONDS:
                self.root.destroy()
                return
        else:
            self.empty_since = None

        active_projects = [d.get("project", "?") for d in sessions.values()]
        changed_layout = False

        # Sesion cerrada: el buho se despide; se retira cuando termina la animacion.
        for sid, owl in self.owls.items():
            if sid not in sessions and not owl.get("leaving"):
                owl["leaving"] = True
                owl["anim"].set_state("bye")

        for sid, d in sessions.items():
            state = self.effective_state(d)
            owl = self.owls.get(sid)
            if owl is not None and owl.get("leaving"):
                continue  # termina de despedirse; si la sesion sigue, vuelve en el siguiente ciclo
            if owl is None:
                project = d.get("project", "?")
                palette = self.colors.color_for(project, active_projects)
                self.owls[sid] = {"anim": OwlAnimation(self.sprites, state), "palette": palette,
                                  "project": project, "state": state}
                self.order.append(sid)
                changed_layout = True
            elif owl["state"] != state:
                if state in SOUND_STATES and winsound:
                    winsound.MessageBeep(getattr(winsound, SOUND_STATES[state]))
                owl["anim"].set_state(state)
                owl["state"] = state

        if changed_layout:
            self.layout()
        self.root.after(POLL_MS, self.poll)

    # --- dibujo
    def layout(self):
        self.canvas.delete("all")
        n = max(len(self.order), 1)
        width = n * self.owl_w + (n - 1) * GAP
        height = self.owl_h + 2 + PILL_H
        self.canvas.config(width=width, height=height)
        self.root.geometry(f"{width}x{height}+{self.right_edge - width}+{self.top}")

        if not self.order:
            self._pill(width / 2, self.owl_h + 2, "sin agentes", "empty")
        for idx, sid in enumerate(self.order):
            owl = self.owls[sid]
            x = idx * (self.owl_w + GAP)
            tag = f"owl-{sid}"
            layers, dy = owl["anim"].frame_key()
            owl["image_item"] = self.canvas.create_image(
                x, 0, anchor="nw", image=self.renderer.image(owl["palette"], layers, dy), tags=tag)
            self._pill(x + self.owl_w / 2, self.owl_h + 2, owl["project"], tag)

    def _pill(self, cx, top, text, tag):
        max_chars = max(4, self.owl_w // 7)
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
        for sid, owl in self.owls.items():
            owl["anim"].tick(dt)
            if owl.get("leaving") and owl["anim"].finished():
                gone.append(sid)
                continue
            if "image_item" in owl:
                layers, dy = owl["anim"].frame_key()
                self.canvas.itemconfig(owl["image_item"],
                                       image=self.renderer.image(owl["palette"], layers, dy))
        if gone:
            for sid in gone:
                del self.owls[sid]
                self.order.remove(sid)
            self.layout()
        self.root.after(FRAME_MS, self.animate)


if __name__ == "__main__":
    # Instancia unica: si el puerto ya esta tomado, otro widget esta abierto.
    _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock.bind(("127.0.0.1", 47823))
    except OSError:
        raise SystemExit(0)
    Widget().root.mainloop()
