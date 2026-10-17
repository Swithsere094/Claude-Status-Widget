# Claude Code Status Widget

Widget flotante para Windows que muestra en tiempo real el estado de tus sesiones de Claude Code (terminal o VS Code), para que puedas trabajar en otra cosa mientras los agentes corren en segundo plano.

| Indicador | Estado |
|---|---|
| ⚪ inactiva | Sesión abierta, sin tareas |
| 🟡 trabajando | El agente está ejecutando una tarea |
| 🟢 listo | El agente terminó (suena un aviso) |
| 🔴 te espera | Necesita aprobación o tu respuesta (suena un aviso) |

## Cómo funciona

- Los **hooks** de Claude Code ejecutan `claude_status.py` en cada evento de la sesión. El script guarda el estado en `~/.claude/status/<session_id>.json`, junto con el PID del proceso de Claude Code.
- `claude_widget.pyw` lee esa carpeta cada segundo y muestra una fila por sesión.
- El widget se abre solo al iniciar una sesión, y nunca hay más de uno abierto.
- Si una sesión se cierra (con `/exit`, con la X de la terminal o cerrando VS Code), su fila desaparece. Cuando no queda ninguna sesión, el widget se cierra solo.

## Requisitos

- Windows
- Python 3.8+ en el PATH (`python` o `py`)
- Claude Code (CLI o extensión de VS Code)

## Instalación

1. Instala la dependencia:
   ```
   python -m pip install -r requirements.txt
   ```
2. Copia `claude_status.py` y `claude_widget.pyw` a `C:\Users\TU_USUARIO\.claude\`.
3. Agrega el bloque `"hooks"` de `settings.example.json` a `C:\Users\TU_USUARIO\.claude\settings.json`:
   - Reemplaza `TU_USUARIO` por tu usuario de Windows. Puedes verlo con `echo $env:USERNAME` en PowerShell.
   - Usa barras `/` en las rutas.
   - Si ya tienes otras claves en el archivo, separa el bloque `"hooks"` con una coma.
   - Si `python` abre la Microsoft Store, usa `py` en los comandos.
4. Reinicia tus sesiones de Claude Code.

## Uso

- **Arrastrar** (clic izquierdo): mueve el widget.
- **Doble clic** sobre una fila: descarta esa sesión.
- **Clic derecho**: cierra el widget. Se vuelve a abrir con la próxima sesión.

## Solución de problemas

- **El widget no aparece.** Ejecuta en PowerShell:
  ```
  python C:/Users/TU_USUARIO/.claude/claude_status.py start
  ```
  y revisa el error que muestre.
- **No se crean archivos en `~/.claude/status/`.** Revisa que el JSON de `settings.json` sea válido (sin comas faltantes o sobrantes).
- **`ModuleNotFoundError: psutil`.** Instala psutil con el mismo intérprete de los hooks (`python -m pip install psutil` o `py -m pip install psutil`).
