"""Simula sesiones de Claude Code para probar el widget sin abrir Claude.

Uso:
    python tools/simulate.py                       # 4 sesiones que cambian de estado solas
    python tools/simulate.py --mascota whiskers    # todas con la misma mascota
    python tools/simulate.py --sesiones 2 --intervalo 3

Las sesiones simuladas usan el PID de este script, asi que se despiden del widget
en cuanto cierras el simulador (Ctrl+C). El widget nunca las guarda en tu registro
de asignaciones, asi que no afectan las mascotas de tus proyectos reales.
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pet_contract import load_pets  # noqa: E402

STATUS_DIR = Path.home() / ".claude" / "status"
WIDGET = ROOT / "claude_widget.pyw"
PROJECTS = ["api-backend", "sitio-web", "scripts-datos", "widget-buhos", "app-movil"]
NEXT = {"idle": ["working"], "working": ["done", "done", "waiting"], "done": ["idle", "working"],
        "waiting": ["working"]}


def write(sid, project, state, me, pet):
    record = {"project": project, "state": state, "ts": time.time(),
              "pid": me.pid, "pid_ctime": me.create_time(), "simulated": True}
    if pet:
        record["pet"] = pet
    (STATUS_DIR / f"{sid}.json").write_text(json.dumps(record), encoding="utf-8")


def launch_widget():
    """Abre el widget desacoplado, para que el Ctrl+C del simulador no lo cierre de golpe."""
    exe = sys.executable
    opts = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pythonw) if pythonw.exists() else exe
        opts["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        opts["start_new_session"] = True
    subprocess.Popen([exe, str(WIDGET)], **opts)


def main():
    pets, _ = load_pets(ROOT / "pets")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sesiones", type=int, default=4, help="cuantas sesiones simular (1-5)")
    ap.add_argument("--intervalo", type=float, default=4, help="segundos entre cambios de estado")
    ap.add_argument("--mascota", choices=sorted(pets), help="usar solo esta mascota")
    ap.add_argument("--sin-widget", action="store_true", help="no abrir el widget automaticamente")
    args = ap.parse_args()

    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    me = psutil.Process()
    projects = PROJECTS[:max(1, min(args.sesiones, len(PROJECTS)))]
    sessions = {f"sim-{uuid.uuid4().hex[:8]}": [p, "idle"] for p in projects}
    for sid, (project, state) in sessions.items():
        write(sid, project, state, me, args.mascota)
    if not args.sin_widget:
        launch_widget()

    print(f"Simulando {len(sessions)} sesiones" + (f" con {args.mascota}" if args.mascota else "")
          + ". Ctrl+C para terminar.")
    try:
        while True:
            time.sleep(args.intervalo)
            sid = random.choice(list(sessions))
            project, state = sessions[sid]
            new = random.choice(NEXT[state])
            sessions[sid][1] = new
            write(sid, project, new, me, args.mascota)
            print(f"  {project}: {state} -> {new}")
    except KeyboardInterrupt:
        pass
    finally:
        for sid in sessions:
            (STATUS_DIR / f"{sid}.json").unlink(missing_ok=True)
        print("Sesiones simuladas eliminadas.")


if __name__ == "__main__":
    main()
