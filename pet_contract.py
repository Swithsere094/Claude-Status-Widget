"""Contrato que debe cumplir cada mascota (pets/<id>/pet.json) y su validador.

Lo usan el widget, para cargar solo mascotas validas, y tools/check_pets.py,
para revisar una mascota mientras se disena.

Formato de pet.json
-------------------
id, name, species, description   identificacion de la mascota (id = nombre de la carpeta)
width, height                    tamano del lienzo; debe ser WIDTH x HEIGHT
transparent                      caracter que no se dibuja (normalmente ".")
shared_colors                    {caracter: "#rrggbb"} comunes a todas las paletas
palettes                         {id: {"name": "...", caracter: "#rrggbb", ..., "hide_layers"?: [...]}}
                                 hide_layers: capas que ese color no dibuja (marcas propias de otro pelaje)
layers                           {nombre: {"x", "y", "rows": ["...", ...]}}
fixed_layers                     capas que no se mueven con "dy" (globos, signos)
blink (opcional)                 {"targets", "min_ms", "max_ms", "sequence": [[capa, ms], ...]}
animations                       {estado: {"label", "intro"?, "loop", "blink"?, "end"?}}

Cada frame es {"layers": [...], "ms": n, "dx"?: n, "dy"?: n, "dissolve"?: 0..1}.
"dx" y "dy" desplazan las capas (salvo las fijas); lo que sale del lienzo no se dibuja.
"dissolve" borra esa fraccion de pixeles (siempre los mismos), para desvanecer.
"""
import json
from pathlib import Path

WIDTH = 24
HEIGHT = 24
REQUIRED_STATES = ("idle", "working", "done", "waiting", "sleep", "bye")


PALETTE_META = {"name", "hide_layers"}


def palette_colors(palette):
    """Solo los colores de una paleta (sin nombre ni opciones)."""
    return {k: v for k, v in palette.items() if k not in PALETTE_META}


def validate(pet, folder_name=None):
    """Devuelve la lista de errores de una mascota; vacia si cumple el contrato."""
    errors = []

    def err(msg):
        errors.append(msg)

    for key in ("id", "name", "width", "height", "transparent", "shared_colors",
                "palettes", "layers", "animations"):
        if key not in pet:
            err(f"falta la clave '{key}'")
    if errors:
        return errors

    if folder_name and pet["id"] != folder_name:
        err(f"el id '{pet['id']}' no coincide con la carpeta '{folder_name}'")
    if (pet["width"], pet["height"]) != (WIDTH, HEIGHT):
        err(f"el lienzo debe ser {WIDTH}x{HEIGHT}, no {pet['width']}x{pet['height']}")
    if not pet["palettes"]:
        err("necesita al menos una paleta")

    transparent = pet["transparent"]
    shared = set(pet["shared_colors"])
    for pid, pal in pet["palettes"].items():
        if "name" not in pal:
            err(f"la paleta '{pid}' no tiene 'name'")
        for name in pal.get("hide_layers", []):
            if name not in pet["layers"]:
                err(f"paleta '{pid}': hide_layers nombra la capa '{name}', que no existe")
    palette_chars = [palette_colors(p).keys() for p in pet["palettes"].values()]
    palette_chars = [set(k) for k in palette_chars]
    common_palette_chars = set.intersection(*palette_chars) if palette_chars else set()
    if palette_chars and any(c != palette_chars[0] for c in palette_chars):
        err("todas las paletas deben definir los mismos caracteres")
    known = shared | common_palette_chars | {transparent}

    layers = pet["layers"]
    for name, L in layers.items():
        rows = L.get("rows") or []
        if not rows:
            err(f"capa '{name}': sin filas")
            continue
        widths = [len(r) for r in rows]
        w = max(set(widths), key=widths.count)  # el ancho mas comun es la referencia
        for i, r in enumerate(rows):
            if len(r) != w:
                err(f"capa '{name}', fila {i}: ancho {len(r)}, se esperaba {w}")
            unknown = set(r) - known
            if unknown:
                err(f"capa '{name}', fila {i}: caracteres sin color {sorted(unknown)}")
        x, y = L.get("x", 0), L.get("y", 0)
        if x < 0 or y < 0 or x + w > WIDTH or y + len(rows) > HEIGHT:
            err(f"capa '{name}': se sale del lienzo")

    for name in pet.get("fixed_layers", []):
        if name not in layers:
            err(f"fixed_layers: la capa '{name}' no existe")

    blink = pet.get("blink")
    if blink:
        for name in blink.get("targets", []):
            if name not in layers:
                err(f"blink.targets: la capa '{name}' no existe")
        for step in blink.get("sequence", []):
            if step[0] not in layers:
                err(f"blink.sequence: la capa '{step[0]}' no existe")
        if not blink.get("sequence"):
            err("blink: la secuencia esta vacia")

    anims = pet["animations"]
    for state in REQUIRED_STATES:
        if state not in anims:
            err(f"falta la animacion obligatoria '{state}'")
    for state, a in anims.items():
        if not a.get("loop"):
            err(f"animacion '{state}': necesita un 'loop' con al menos un frame")
        if a.get("blink") and not blink:
            err(f"animacion '{state}': usa parpadeo pero la mascota no define 'blink'")
        for part in ("intro", "loop"):
            for i, f in enumerate(a.get(part, [])):
                where = f"animacion '{state}', {part} frame {i}"
                if not isinstance(f.get("ms"), (int, float)) or f["ms"] <= 0:
                    err(f"{where}: 'ms' debe ser un numero mayor que 0")
                for name in f.get("layers", []):
                    if name not in layers:
                        err(f"{where}: la capa '{name}' no existe")
                for axis in ("dx", "dy"):
                    if not isinstance(f.get(axis, 0), int):
                        err(f"{where}: '{axis}' debe ser un entero")
                d = f.get("dissolve", 0)
                if not 0 <= d <= 1:
                    err(f"{where}: 'dissolve' debe estar entre 0 y 1")
    bye = anims.get("bye")
    if bye and not (bye.get("end") and bye.get("intro")):
        err("animacion 'bye': necesita 'intro' y \"end\": true")
    return errors


def load_pets(pets_dir):
    """Carga todas las mascotas validas. Devuelve (mascotas, errores por carpeta)."""
    pets, problems = {}, {}
    for f in sorted(Path(pets_dir).glob("*/pet.json")):
        folder = f.parent.name
        try:
            pet = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            problems[folder] = [f"no se pudo leer pet.json: {e}"]
            continue
        errors = validate(pet, folder)
        if errors:
            problems[folder] = errors
        else:
            pets[pet["id"]] = pet
    return pets, problems
