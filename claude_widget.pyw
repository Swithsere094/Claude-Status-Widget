"""Widget flotante que muestra el estado de tus agentes de Claude Code.
- Arrastrar con clic izquierdo para moverlo.
- Doble clic sobre una sesion para descartarla.
- Clic derecho para cerrar el widget.
- Se cierra solo cuando no queda ninguna sesion de Claude Code abierta.
Requiere: pip install psutil
"""
import json
import socket
import time
import tkinter as tk
import winsound
from pathlib import Path

import psutil

STATUS_DIR = Path.home() / ".claude" / "status"
STALE_SECONDS = 6 * 3600   # respaldo si no se pudo identificar el proceso
EMPTY_CLOSE_SECONDS = 5    # se cierra tras 5 s sin sesiones
BG = "#1e1e1e"
COLORS = {"idle": "#888888", "working": "#f5b400", "done": "#2ecc71", "waiting": "#e74c3c"}
LABELS = {"idle": "inactiva", "working": "trabajando", "done": "listo", "waiting": "te espera"}
FONT = ("Segoe UI", 9)


def session_alive(d):
    """True si el proceso de Claude Code de esa sesion sigue vivo."""
    if "pid" not in d:              # archivo de la version anterior
        return False
    pid = d["pid"]
    if pid is None:                 # no se identifico el proceso: usar caducidad
        return time.time() - d.get("ts", 0) < STALE_SECONDS
    try:
        # Comparar la hora de creacion evita confundirse si Windows reutiliza el PID.
        return abs(psutil.Process(pid).create_time() - (d.get("pid_ctime") or 0)) < 1
    except psutil.Error:
        return False


class Widget:
    def __init__(self):
        self.root = tk.Tk()
        r = self.root
        r.overrideredirect(True)          # sin bordes
        r.attributes("-topmost", True)    # siempre encima
        r.attributes("-alpha", 0.92)
        r.configure(bg=BG)
        r.geometry(f"+{r.winfo_screenwidth() - 280}+40")

        self.frame = tk.Frame(r, bg=BG, padx=10, pady=6)
        self.frame.pack()
        self.prev_states = {}
        self.empty_since = None

        r.bind_all("<ButtonPress-1>", self._start_drag)
        r.bind_all("<B1-Motion>", self._drag)
        r.bind_all("<Button-3>", lambda e: r.destroy())

        STATUS_DIR.mkdir(parents=True, exist_ok=True)
        self.refresh()

    def _start_drag(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def _drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def load_sessions(self):
        sessions = {}
        for f in STATUS_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not session_alive(d):
                f.unlink(missing_ok=True)
                continue
            sessions[f.stem] = (d, f)
        return sessions

    def notify_changes(self, sessions):
        for sid, (d, _) in sessions.items():
            old, new = self.prev_states.get(sid), d.get("state")
            if old and old != new:
                if new == "done":
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                elif new == "waiting":
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        self.prev_states = {sid: d.get("state") for sid, (d, _) in sessions.items()}

    def refresh(self):
        sessions = self.load_sessions()

        if not sessions:
            self.empty_since = self.empty_since or time.time()
            if time.time() - self.empty_since > EMPTY_CLOSE_SECONDS:
                self.root.destroy()
                return
        else:
            self.empty_since = None

        self.notify_changes(sessions)

        for w in self.frame.winfo_children():
            w.destroy()

        if not sessions:
            tk.Label(self.frame, text="Claude · sin agentes", fg="#888", bg=BG, font=FONT).pack(anchor="w")

        for sid, (d, f) in sorted(sessions.items(), key=lambda x: x[1][0].get("project", "")):
            state = d.get("state", "done")
            mins = int((time.time() - d.get("ts", time.time())) // 60)
            row = tk.Frame(self.frame, bg=BG)
            row.pack(anchor="w", fill="x")
            dot = tk.Label(row, text="●", fg=COLORS.get(state, "#888"), bg=BG, font=("Segoe UI", 12))
            dot.pack(side="left")
            txt = tk.Label(row, text=f"{d.get('project', '?')} · {LABELS.get(state, state)} · {mins} min",
                           fg="#ddd", bg=BG, font=FONT)
            txt.pack(side="left", padx=4)
            for w in (row, dot, txt):
                w.bind("<Double-Button-1>", lambda e, f=f: f.unlink(missing_ok=True))

        self.root.after(1000, self.refresh)


if __name__ == "__main__":
    # Instancia unica: si el puerto ya esta tomado, otro widget esta abierto.
    _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock.bind(("127.0.0.1", 47823))
    except OSError:
        raise SystemExit(0)
    Widget().root.mainloop()
