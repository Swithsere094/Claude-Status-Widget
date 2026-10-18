"""Revisa que cada mascota de pets/ cumpla el contrato del widget.

Uso:
    python tools/check_pets.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pet_contract import REQUIRED_STATES, load_pets  # noqa: E402


def main():
    pets, problems = load_pets(ROOT / "pets")
    for pid, pet in pets.items():
        print(f"OK     {pet['name']} ({pid}): {len(pet['palettes'])} paletas, "
              f"{len(pet['layers'])} capas, {len(pet['animations'])} animaciones")
    for folder, errors in problems.items():
        print(f"ERROR  {folder}:")
        for e in errors:
            print(f"         - {e}")
    if not pets and not problems:
        print("No hay mascotas en pets/.")
    print(f"\nEstados obligatorios: {', '.join(REQUIRED_STATES)}")
    sys.exit(1 if problems or not pets else 0)


if __name__ == "__main__":
    main()
