# Mascotas de Claude Code

Widget flotante para Windows que muestra una mascota animada por cada sesión de Claude Code (terminal o VS Code). Así ves de un vistazo qué agentes siguen trabajando, cuáles terminaron y cuáles te esperan, mientras haces otra cosa.

| Estado | Qué hace la mascota |
|---|---|
| inactiva | Reposa y parpadea a intervalos aleatorios |
| trabajando | Teclea en su portátil |
| listo | Celebra y queda con un ✓ encima (suena un aviso) |
| te espera | Pide atención con un "!" (suena un aviso). Solo cuando necesita un permiso o que respondas una pregunta |
| dormido | Tras 10 minutos inactiva o lista, se duerme |
| despedida | Al cerrarse la sesión, se despide y sale de escena |

## Mascotas

Hay cuatro mascotas, cada una con cinco colores y su propia forma de vivir cada estado.

### Bubo, el búho

Parpadea, teclea en su portátil, da un saltito al terminar, levanta el ala con un "!" cuando te espera y, al despedirse, saluda y sale volando.

| Color | Tono principal |
|---|---|
| Petróleo | `#2a9d8f` |
| Violeta | `#8a6bd1` |
| Naranja | `#d96f4b` |
| Cielo | `#4a8fe7` |
| Rosa | `#e06c9f` |

### Bolt, el robot

Tiene un LED en la antena que indica el estado: cian en reposo, amarillo titilando mientras trabaja, verde al terminar, rojo cuando te espera y apagado cuando duerme. Levanta el brazo para llamarte y se despide con un propulsor.

| Color | Tono principal |
|---|---|
| Acero | `#a9b4c2` |
| Cobre | `#c9825a` |
| Menta | `#7fd1b0` |
| Grafito | `#5d6573` |
| Latón | `#d9b74f` |

### Whiskers, el gato

Mece la cola en reposo, trabaja con las patas sobre el teclado, se estira antes de celebrar, maúlla con la cola parada cuando te espera, duerme echado con la cola enroscada y se despide saliendo de un salto.

| Color | Pelaje |
|---|---|
| Atigrado | Naranja con rayas |
| Bicolor | Blanco con capucha y cola negras, ojos amarillo verdoso |
| Negro | Negro con ojos amarillos |
| Crema | Crema con rayas suaves y ojos azules |
| Calicó | Blanco con manchas naranja y negras |

### Mist, el fantasma

Siempre flota con el borde ondulando. Da una vuelta al terminar, abre la boquita cuando te espera y, al despedirse, se desvanece píxel a píxel mientras sube.

| Color | Tono principal |
|---|---|
| Blanco | `#eef2f7` |
| Lila | `#dccbf6` |
| Menta | `#c4f0dc` |
| Celeste | `#c6e4fb` |
| Rosa | `#fbd0e0` |

### Cómo se asignan

Cada proyecto (carpeta) recibe al azar una mascota y uno de sus colores la primera vez que aparece, y los conserva para siempre. Al asignar se evita repetir lo que ya está en pantalla: primero se elige una mascota que no se esté mostrando y, si ya están las cuatro, una combinación de mascota y color que no esté en uso.

## Cómo funciona

- Los **hooks** de Claude Code ejecutan `claude_status.py` en cada evento de la sesión. El script guarda el estado en `~/.claude/status/<session_id>.json`, junto con el PID del proceso de Claude Code.
- `claude_widget.pyw` lee esa carpeta cada segundo y anima una mascota por sesión. Las mascotas se cargan de `pets/<id>/pet.json`.
- El widget se abre solo al iniciar una sesión, y nunca hay más de uno abierto.
- Una sesión recién abierta e inactiva espera 3 segundos antes de mostrar su mascota. La extensión de VS Code a veces lanza un proceso extra que cierra al segundo, y así ese proceso nunca aparece. Si la sesión empieza a trabajar o pide algo, su mascota aparece de inmediato.
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
python tools/preview.py       # genera preview.html con todas las mascotas animadas
```

`simulate.py` acepta `--sesiones 1-5`, `--intervalo <segundos>`, `--mascota <bubo|bolt|whiskers|mist>` para ver solo una mascota y `--sin-widget`. Las sesiones simuladas nunca se guardan en el registro de asignaciones, así que no cambian las mascotas de tus proyectos. Con `Ctrl+C` las sesiones se despiden y el widget se cierra solo.

`preview.py` crea `preview.html` en la raíz del proyecto; ábrelo en el navegador para ver cada mascota en sus 6 estados y 5 colores.

## Crear o editar mascotas

Cada mascota vive en su carpeta, `pets/<id>/pet.json`, y debe cumplir el contrato descrito en `pet_contract.py`:

- Lienzo de 24×24 píxeles. El widget lo dibuja a escala ×4.
- Las 6 animaciones obligatorias: `idle`, `working`, `done`, `waiting`, `sleep` y `bye` (esta última con `"end": true`).
- Capas de pixel art como cuadrículas de caracteres; cada carácter es un color de la paleta y `.` es transparente.
- Cada frame lista sus capas y su duración, y puede desplazarlas (`dx`, `dy`) o desvanecerlas (`dissolve`, de 0 a 1).
- Cada color puede ocultar capas con `hide_layers`, para marcas que solo tiene un pelaje (como la capucha del bicolor o las manchas del calicó).
- Parpadeo opcional.

Después de editar, corre `python tools/check_pets.py` y revisa el resultado con `python tools/preview.py`.

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
- **Diagnóstico de eventos.** Crea un archivo vacío llamado `claude_widget_debug` en `~/.claude/`. Desde ese momento, cada evento de Claude Code se anota en `~/.claude/claude_status_debug.log` con su sesión, su origen y la cadena de procesos. Borra el archivo para desactivarlo.
- **`ModuleNotFoundError: psutil`.** Instala psutil con el mismo intérprete de los hooks (`python -m pip install psutil` o `py -m pip install psutil`).

## Licencia

[MIT](LICENSE) © 2026 Daniel Jesús Castillo Botero
