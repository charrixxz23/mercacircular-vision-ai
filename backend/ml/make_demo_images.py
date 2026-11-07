"""Genera las imágenes de ejemplo de demo-data/images a partir de Fruits-360.

    python -m ml.make_demo_images

Todas provienen de grupos de PRUEBA (no vistos en entrenamiento). Se elige el
primer archivo de cada grupo en orden alfabético, sin seleccionar a mano los
que el modelo acierta. Cambios realizados (exigido por CC BY-SA 4.0): la fruta
se coloca sobre un fondo de bandeja; en dos imágenes se agregan manchas
sintéticas o desenfoque para probar el detector y la validación de calidad.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.vision.segmentation import segment  # noqa: E402
from ml.augment import add_blemishes, object_mask  # noqa: E402
from ml.dataset import DEFAULT_DATA  # noqa: E402

OUT = BACKEND.parent / "demo-data" / "images"
CANVAS = 220


def on_tray(img: np.ndarray) -> np.ndarray:
    """Fruta centrada sobre una bandeja gris claro con un leve gradiente de luz."""
    m = object_mask(img)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:CANVAS, 0:CANVAS].astype(np.float32) / CANVAS
    bg = np.dstack([np.full((CANVAS, CANVAS), c, np.float32) for c in (200, 206, 210)])
    bg += ((1 - yy) * 18 - xx * 8)[..., None]
    rng = np.random.default_rng(1)
    bg += rng.normal(0, 2.5, bg.shape)
    oy, ox = (CANVAS - h) // 2, (CANVAS - w) // 2
    alpha = cv2.GaussianBlur(m, (3, 3), 0).astype(np.float32)[..., None] / 255.0
    bg[oy:oy + h, ox:ox + w] = alpha * img + (1 - alpha) * bg[oy:oy + h, ox:ox + w]
    return np.clip(bg, 0, 255).astype(np.uint8)


def first(group: str) -> np.ndarray:
    path = sorted((DEFAULT_DATA / "Test" / group).glob("*.jpg"))[0]
    return cv2.imread(str(path)), path.name


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    items = []

    def save(name: str, img: np.ndarray, product: str, group: str, src: str, change: str, purpose: str):
        cv2.imwrite(str(OUT / name), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        items.append({"archivo": name, "producto": product, "grupo_fruits360": group, "archivo_original": src,
                      "cambios": change, "proposito": purpose})

    tomato, src = first("Tomato 3")
    base = on_tray(tomato)
    save("tomate_bandeja.jpg", base, "tomate", "Tomato 3", src, "Fruta colocada sobre fondo de bandeja.",
         "Tomate sin manchas visibles.")
    dirty, _, _ = add_blemishes(base, segment(base).main_mask, np.random.default_rng(4), drop=60, n=2)
    save("tomate_manchas_sinteticas.jpg", dirty, "tomate", "Tomato 3", src,
         "Fondo de bandeja + 2 manchas oscuras SINTÉTICAS pintadas por ml/augment.py.",
         "Probar el detector de manchas (las manchas no son defectos reales).")
    blurred = cv2.GaussianBlur(base, (0, 0), 3.0)
    save("tomate_desenfocado.jpg", blurred, "tomate", "Tomato 3", src, "Fondo de bandeja + desenfoque gaussiano (σ = 3).",
         "Probar la validación de calidad (debe pedir otra foto).")
    banana, src = first("Banana 3")
    save("banano_bandeja.jpg", on_tray(banana), "banano", "Banana 3", src, "Fruta colocada sobre fondo de bandeja.",
         "Banano de prueba.")
    potato, src = first("Potato Red 2")
    save("papa_bandeja.jpg", on_tray(potato), "papa", "Potato Red 2", src, "Fruta colocada sobre fondo de bandeja.",
         "Papa roja de prueba (clase con baja sensibilidad del modelo).")

    meta = {
        "_aviso": "Imágenes derivadas de Fruits-360 (Mihai Oltean, CC BY-SA 4.0, https://github.com/fruits-360). "
                  "Se distribuyen bajo la misma licencia. Las manchas de 'tomate_manchas_sinteticas.jpg' son artificiales.",
        "licencia": "CC BY-SA 4.0",
        "imagenes": items,
    }
    (OUT / "samples.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(items)} imágenes en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
