"""Hook de Claude Code: registra el estado de cada sesion para el widget.
Uso: python claude_status.py <start|working|done|waiting|end>
Claude Code envia por stdin un JSON con session_id y cwd.
Requiere: pip install psutil
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

CLAUDE_DIR = Path.home() / ".claude"
STATUS_DIR = CLAUDE_DIR / "status"
# Diagnostico: si existe este archivo (vacio), cada evento se anota en DEBUG_LOG.
DEBUG_FLAG = CLAUDE_DIR / "claude_widget_debug"
DEBUG_LOG = CLAUDE_DIR / "claude_status_debug.log"
CLAUDE_NAMES = {"claude.exe", "claude", "node.exe", "node"}


def find_claude_process():
    """Sube por el arbol de procesos hasta encontrar el proceso de Claude Code."""
    try:
        p = psutil.Process(os.getpid()).parent()
        while p is not None:
            if p.name().lower() in CLAUDE_NAMES:
                return p
            p = p.parent()
    except psutil.Error:
        pass
    return None


def debug(state, data, proc):
    """Anota el evento y la cadena de procesos padre, solo si el diagnostico esta activo."""
    if not DEBUG_FLAG.exists():
        return
    chain = []
    try:
        p = psutil.Process(os.getpid()).parent()
        while p is not None and len(chain) < 8:
            chain.append(f"{p.name()}:{p.pid}")
            p = p.parent()
    except psutil.Error:
        pass
    keys = ("hook_event_name", "source", "reason", "notification_type", "session_id", "cwd")
    info = " ".join(f"{k}={data[k]}" for k in keys if k in data)
    line = (f"{time.strftime('%H:%M:%S')} {state:8} {info} "
            f"claude_pid={proc.pid if proc else None} cadena={' > '.join(chain)}\n")
    try:
        with DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def launch_widget():
    """Lanza el widget desacoplado; si ya hay uno abierto, el nuevo se cierra solo."""
    widget = Path(__file__).with_name("claude_widget.pyw")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pythonw) if pythonw.exists() else sys.executable
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, str(widget)], creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


state = sys.argv[1] if len(sys.argv) > 1 else "done"
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
proc = find_claude_process()
debug(state, data, proc)

# "te espera" es solo para lo que necesita respuesta (permisos, preguntas).
# El aviso de inactividad (idle_prompt) llega aunque ya haya terminado: se ignora.
if state == "waiting" and (data.get("notification_type") == "idle_prompt"
                           or "waiting for your input" in str(data.get("message", "")).lower()):
    sys.exit(0)

session_id = data.get("session_id", "desconocida")
cwd = data.get("cwd", os.getcwd())

STATUS_DIR.mkdir(parents=True, exist_ok=True)
status_file = STATUS_DIR / f"{session_id}.json"

if state == "end":
    status_file.unlink(missing_ok=True)
    sys.exit(0)

record = {
    "project": Path(cwd).name,
    "state": "idle" if state == "start" else state,
    "ts": time.time(),
    "pid": proc.pid if proc else None,
    "pid_ctime": proc.create_time() if proc else None,
}
status_file.write_text(json.dumps(record), encoding="utf-8")

if state == "start":
    launch_widget()
