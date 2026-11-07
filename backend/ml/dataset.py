"""Inventario reproducible de imágenes por clase, grupo y partición."""

from __future__ import annotations

import json
import math
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "data" / "fruits-360"

# Muestras por clase. Los fotogramas de una misma grabación son casi idénticos,
# así que tomar todos no aporta información y solo alarga el entrenamiento.
TARGET_PER_CLASS = {"train": 720, "test": 300}


@dataclass(frozen=True)
class Sample:
    path: Path
    label: str
    group: str
    split: str

    @property
    def seed(self) -> int:
        """Semilla estable por imagen: el mismo fondo aleatorio en cada ejecución."""
        return zlib.crc32(f"{self.split}/{self.group}/{self.path.name}".encode())


def load_splits() -> dict:
    return json.loads((HERE / "splits.json").read_text(encoding="utf-8"))


def build(data_dir: Path = DEFAULT_DATA) -> list[Sample]:
    splits = load_splits()
    samples: list[Sample] = []
    for label, parts in splits["clases"].items():
        for split in ("train", "test"):
            groups = parts[split]
            per_group = math.ceil(TARGET_PER_CLASS[split] / len(groups))
            for group in groups:
                files = sorted((data_dir / "Training" / group).glob("*.jpg")) + sorted((data_dir / "Test" / group).glob("*.jpg"))
                if not files:
                    raise FileNotFoundError(f"No hay imágenes para '{group}'. Ejecute: python -m ml.download_dataset")
                rng = np.random.default_rng(zlib.crc32(group.encode()))
                take = rng.choice(len(files), size=min(per_group, len(files)), replace=False)
                samples += [Sample(files[i], label, group, split) for i in sorted(take)]
    return samples
