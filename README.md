# Búhos de Claude Code

Widget flotante para Windows que muestra un búho animado por cada sesión de Claude Code (terminal o VS Code). Así ves de un vistazo qué agentes siguen trabajando, cuáles terminaron y cuáles te esperan, mientras haces otra cosa.

| Estado | Qué hace el búho |
|---|---|
| inactiva | Sentado, parpadea a intervalos aleatorios |
| trabajando | Teclea en su portátil |
| listo | Da un saltito y queda con un ✓ encima (suena un aviso) |
| te espera | Levanta el ala con un "!" y rebota (suena un aviso). Necesita una aprobación o tu respuesta |
| dormido | Tras 10 minutos inactivo o listo, se duerme |
| despedida | Al cerrarse la sesión, saluda con el ala y sale volando |

Cada proyecto (carpeta) tiene su propio color entre cinco: petróleo, violeta, naranja, cielo y rosa. El color se asigna la primera vez que aparece el proyecto, eligiendo uno que no esté en uso por otra sesión abierta, y se conserva para siempre.

## Cómo funciona

- Los **hooks** de Claude Code ejecutan `claude_status.py` en cada evento de la sesión. El script guarda el estado en `~/.claude/status/<session_id>.json`, junto con el PID del proceso de Claude Code.
- `claude_widget.pyw` lee esa carpeta cada segundo y anima un búho por sesión. Los sprites, colores y animaciones vienen de `sprites/owl.json`.
- El widget se abre solo al iniciar una sesión, y nunca hay más de uno abierto.
- Si una sesión se cierra (con `/exit`, con la X de la terminal o cerrando VS Code), su búho se despide y sale volando. Cuando no queda ninguna sesión, el widget se cierra solo.
- Los colores asignados se guardan en `~/.claude/claude_widget_colors.json`. Bórralo si quieres reasignarlos.

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
   - la carpeta `sprites` completa (el widget busca `sprites\owl.json` junto a él)
3. Agrega el bloque `"hooks"` de `settings.example.json` a `C:\Users\TU_USUARIO\.claude\settings.json`:
   - Reemplaza `TU_USUARIO` por tu usuario de Windows. Puedes verlo con `echo $env:USERNAME` en PowerShell.
   - Usa barras `/` en las rutas.
   - Si ya tienes otras claves en el archivo, separa el bloque `"hooks"` con una coma.
   - Si `python` abre la Microsoft Store, usa `py` en los comandos.
4. Reinicia tus sesiones de Claude Code.

## Uso

- **Arrastrar** (clic izquierdo sobre un búho): mueve el widget. Las zonas transparentes dejan pasar los clics a lo que hay debajo, así que hay que agarrar al búho o su etiqueta.
- **Doble clic** sobre un búho: descarta esa sesión. Vuelve a aparecer en el siguiente evento de Claude Code.
- **Clic derecho**: cierra el widget. Se vuelve a abrir con la próxima sesión.

## Probar sin Claude Code

```
python tools/simulate.py
```

Abre el widget con 4 sesiones falsas que cambian de estado cada pocos segundos. Con `Ctrl+C` se eliminan y el widget se cierra solo. Opciones: `--sesiones 1-5`, `--intervalo <segundos>`, `--sin-widget`.

## Personalizar

En la cabecera de `claude_widget.pyw`:

- `SCALE`: tamaño del búho. Debe ser un entero para que el pixel art se vea nítido. Por defecto usa el de `owl.json` (×4, 96 px de ancho).
- `SLEEP_AFTER`: segundos antes de que un búho inactivo se duerma.

En `sprites/owl.json` están las paletas (`palettes`), las capas de pixel art (`layers`) y las animaciones (`animations`). Cada capa es una cuadrícula de caracteres, y cada carácter es un color de la paleta (`.` es transparente).

## Solución de problemas

- **El widget no aparece.** Ejecuta en PowerShell:
  ```
  python C:/Users/TU_USUARIO/.claude/claude_status.py start
  ```
  y revisa el error que muestre. Si dice que no encuentra `owl.json`, copia la carpeta `sprites` junto a `claude_widget.pyw`.
- **No se crean archivos en `~/.claude/status/`.** Revisa que el JSON de `settings.json` sea válido (sin comas faltantes o sobrantes).
- **`ModuleNotFoundError: psutil`.** Instala psutil con el mismo intérprete de los hooks (`python -m pip install psutil` o `py -m pip install psutil`).
