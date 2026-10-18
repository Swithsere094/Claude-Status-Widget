"""Simula sesiones de Claude Code para probar el widget sin abrir Claude.

Uso:
    python tools/simulate.py            # 4 sesiones que cambian de estado solas
    python tools/simulate.py --sesiones 2 --intervalo 3

Las sesiones falsas usan el PID de este script, asi que desaparecen del widget
en cuanto cierras el simulador (Ctrl+C).
"""
import argparse
import json
import random
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil

STATUS_DIR = Path.home() / ".claude" / "status"
WIDGET = Path(__file__).resolve().parent.parent / "claude_widget.pyw"
PROJECTS = ["api-backend", "sitio-web", "scripts-datos", "widget-buhos", "app-movil"]
NEXT = {"idle": ["working"], "working": ["done", "done", "waiting"], "done": ["idle", "working"],
        "waiting": ["working"]}


def write(sid, project, state, me):
    record = {"project": project, "state": state, "ts": time.time(),
              "pid": me.pid, "pid_ctime": me.create_time()}
    (STATUS_DIR / f"{sid}.json").write_text(json.dumps(record), encoding="utf-8")


def launch_widget():
    exe = sys.executable
    if sys.platform == "win32":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pythonw) if pythonw.exists() else exe
    subprocess.Popen([exe, str(WIDGET)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sesiones", type=int, default=4, help="cuantas sesiones simular (1-5)")
    ap.add_argument("--intervalo", type=float, default=4, help="segundos entre cambios de estado")
    ap.add_argument("--sin-widget", action="store_true", help="no abrir el widget automaticamente")
    args = ap.parse_args()

    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    me = psutil.Process()
    sessions = {f"sim-{uuid.uuid4().hex[:8]}": [p, "idle"] for p in PROJECTS[:max(1, min(args.sesiones, 5))]}
    for sid, (project, state) in sessions.items():
        write(sid, project, state, me)
    if not args.sin_widget:
        launch_widget()

    print("Simulando", len(sessions), "sesiones. Ctrl+C para terminar.")
    try:
        while True:
            time.sleep(args.intervalo)
            sid = random.choice(list(sessions))
            project, state = sessions[sid]
            new = random.choice(NEXT[state])
            sessions[sid][1] = new
            write(sid, project, new, me)
            print(f"  {project}: {state} -> {new}")
    except KeyboardInterrupt:
        pass
    finally:
        for sid in sessions:
            (STATUS_DIR / f"{sid}.json").unlink(missing_ok=True)
        print("Sesiones simuladas eliminadas.")


if __name__ == "__main__":
    main()
