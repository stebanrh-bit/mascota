"""Estado y preferencias; independientes de la interfaz gráfica."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Character:
    name: str
    kind: str
    body: str
    belly: str
    accent: str
    eyes: str
    description: str


CHARACTERS = {
    "sombra": Character("Sombra", "dragon", "#11141e", "#242938", "#1368dd", "#50d9ff", "Bebé, pero con carácter."),
    "brote": Character("Brote", "dragon", "#184e36", "#bd995c", "#d88935", "#ffe08a", "Un guardián del bosque en miniatura."),
    "nimbo": Character("Nimbo", "spirit", "#b7e9e8", "#e0ffff", "#74b9ff", "#153b55", "Un pequeño espíritu de las nubes."),
}


def clamp_position(x: int, y: int, width: int, height: int, bounds: tuple[int, int, int, int]):
    """Mantiene la ventana visible incluso en monitores con coordenadas negativas."""
    left, top, area_width, area_height = bounds
    return (max(left, min(x, left + max(0, area_width - width))),
            max(top, min(y, top + max(0, area_height - height))))


class Preferences:
    def __init__(self, path: Path):
        self.path = path
        self.character = "sombra"
        self.roaming = True
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if isinstance(data.get("character"), str) and data["character"] in CHARACTERS:
                    self.character = data["character"]
                if isinstance(data.get("roaming"), bool):
                    self.roaming = data["roaming"]
        except (OSError, ValueError):
            pass

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"character": self.character, "roaming": self.roaming}), encoding="utf-8")
        temporary.replace(self.path)
