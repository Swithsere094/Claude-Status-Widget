# Mascotas de Claude Code

Widget flotante para Windows que muestra una mascota animada por cada sesión de Claude Code (terminal o VS Code). Así ves de un vistazo qué agentes siguen trabajando, cuáles terminaron y cuáles te esperan, mientras haces otra cosa.

| Estado | Qué hace la mascota |
|---|---|
| inactiva | Reposa y parpadea a intervalos aleatorios |
| trabajando | Teclea en su portátil |
| listo | Celebra y queda con un ✓ encima (suena un aviso) |
| te espera | Pide atención con un "!" (suena un aviso). Necesita una aprobación o tu respuesta |
| dormido | Tras 10 minutos inactiva o lista, se duerme |
| despedida | Al cerrarse la sesión, se despide y sale de escena |

## Mascotas

| Mascota | Nombre | Colores |
|---|---|---|
| Búho | Bubo | Petróleo, violeta, naranja, cielo, rosa |

Cada proyecto (carpeta) recibe al azar una mascota y uno de sus colores la primera vez que aparece, y los conserva para siempre. Al asignar se evita repetir: primero se elige una mascota que no esté en pantalla y, si todas lo están, una combinación de mascota y color que no esté en uso.

## Cómo funciona

- Los **hooks** de Claude Code ejecutan `claude_status.py` en cada evento de la sesión. El script guarda el estado en `~/.claude/status/<session_id>.json`, junto con el PID del proceso de Claude Code.
- `claude_widget.pyw` lee esa carpeta cada segundo y anima una mascota por sesión. Las mascotas se cargan de `pets/<id>/pet.json`.
- El widget se abre solo al iniciar una sesión, y nunca hay más de uno abierto.
- Si una sesión se cierra (con `/exit`, con la X de la terminal o cerrando VS Code), su mascota se despide. Cuando no queda ninguna sesión, el widget se cierra solo.
- Las asignaciones se guardan en `~/.claude/claude_widget_pets.json`. Bórralo si quieres que se sorteen de nuevo. Si vienes de la versión de solo búhos, tus proyectos conservan su búho y su color.
- Si una mascota no cumple el contrato, el widget la ignora y lo anota en `~/.claude/claude_widget.log`.

## Requisitos

- Windows
- Python 3.8+ en el PATH (`python` o `py`)
- Claude Code (CLI o extensión de VS Code)

## Instalación

1. Instala la dependencia:
   ```
   python -m pip install -r requirements.txt
   ```
2. Copia a `C:\Users\TU_USUARIO\.claude\`:
   - `claude_status.py`
   - `claude_widget.pyw`
   - `pet_contract.py`
   - la carpeta `pets` completa
3. Agrega el bloque `"hooks"` de `settings.example.json` a `C:\Users\TU_USUARIO\.claude\settings.json`:
   - Reemplaza `TU_USUARIO` por tu usuario de Windows. Puedes verlo con `echo $env:USERNAME` en PowerShell.
   - Usa barras `/` en las rutas.
   - Si ya tienes otras claves en el archivo, separa el bloque `"hooks"` con una coma.
   - Si `python` abre la Microsoft Store, usa `py` en los comandos.
4. Reinicia tus sesiones de Claude Code.

Si actualizas desde la versión de solo búhos, borra la carpeta `sprites` de `.claude`: ya no se usa.

## Uso

- **Arrastrar** (clic izquierdo sobre una mascota): mueve el widget. Las zonas transparentes dejan pasar los clics a lo que hay debajo, así que hay que agarrar a la mascota o su etiqueta.
- **Doble clic** sobre una mascota: descarta esa sesión. Vuelve a aparecer en el siguiente evento de Claude Code.
- **Clic derecho**: cierra el widget. Se vuelve a abrir con la próxima sesión.

## Herramientas

```
python tools/simulate.py      # abre el widget con 4 sesiones falsas que cambian de estado
python tools/check_pets.py    # revisa que cada mascota cumpla el contrato
```

`simulate.py` acepta `--sesiones 1-5`, `--intervalo <segundos>` y `--sin-widget`. Con `Ctrl+C` las sesiones falsas se eliminan y el widget se cierra solo.

## Crear o editar mascotas

Cada mascota vive en su carpeta, `pets/<id>/pet.json`, y debe cumplir el contrato descrito en `pet_contract.py`:

- Lienzo de 24×24 píxeles. El widget lo dibuja a escala ×4.
- Las 6 animaciones obligatorias: `idle`, `working`, `done`, `waiting`, `sleep` y `bye` (esta última con `"end": true`).
- Capas de pixel art como cuadrículas de caracteres; cada carácter es un color de la paleta y `.` es transparente.
- Cada frame lista sus capas y su duración, y puede desplazarlas en vertical (`dy`) o desvanecerlas (`dissolve`, de 0 a 1).
- Parpadeo opcional.

Después de editar, corre `python tools/check_pets.py`.

## Personalizar

En la cabecera de `claude_widget.pyw`:

- `SCALE`: tamaño de las mascotas. Debe ser un entero para que el pixel art se vea nítido.
- `SLEEP_AFTER`: segundos antes de que una mascota inactiva se duerma.

## Solución de problemas

- **El widget no aparece.** Revisa `~/.claude/claude_widget.log` y ejecuta en PowerShell:
  ```
  python C:/Users/TU_USUARIO/.claude/claude_status.py start
  ```
  Si dice que no encuentra `pet_contract`, copia `pet_contract.py` y la carpeta `pets` junto a `claude_widget.pyw`.
- **No se crean archivos en `~/.claude/status/`.** Revisa que el JSON de `settings.json` sea válido (sin comas faltantes o sobrantes).
- **`ModuleNotFoundError: psutil`.** Instala psutil con el mismo intérprete de los hooks (`python -m pip install psutil` o `py -m pip install psutil`).
