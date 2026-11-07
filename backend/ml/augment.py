"""Generación de muestras de entrenamiento más parecidas a una foto real.

Fruits-360 tiene fondo blanco perfecto. Para que el modelo aprenda a partir de
la MISMA segmentación que se usa en producción, cada fruta se coloca sobre un
fondo aleatorio (bandeja, mesa, cartón…) con variaciones de iluminación, ruido,
desenfoque leve y compresión JPEG. Las manchas sintéticas para validar el
detector de anomalías también se generan aquí.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.vision.segmentation import fill_holes

# Fondos plausibles en un mercado (BGR).
BACKGROUNDS = [
    (205, 205, 205), (235, 235, 230), (175, 195, 215), (70, 110, 160), (60, 60, 60),
    (150, 95, 45), (35, 35, 35), (190, 190, 170), (120, 150, 170), (90, 140, 90),
]


def object_mask(img: np.ndarray) -> np.ndarray:
    """Máscara del objeto en una imagen de Fruits-360 (fondo rellenado de blanco)."""
    not_white = (np.min(img, axis=2) < 235).astype(np.uint8) * 255
    not_white = cv2.morphologyEx(not_white, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, cc, stats, _ = cv2.connectedComponentsWithStats(not_white, 8)
    if n <= 1:
        return not_white
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (cc == largest).astype(np.uint8) * 255
    return fill_holes(m)


def composite(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Coloca el objeto sobre un fondo aleatorio y aplica variaciones fotométricas."""
    m = object_mask(img)
    h, w = img.shape[:2]
    canvas_side = int(max(h, w) * rng.uniform(1.4, 2.2))
    base = np.array(BACKGROUNDS[rng.integers(len(BACKGROUNDS))], np.float32)
    base = np.clip(base * rng.uniform(0.85, 1.15) + rng.normal(0, 8, 3), 0, 255)
    bg = np.ones((canvas_side, canvas_side, 3), np.float32) * base
    # Gradiente de iluminación.
    gy, gx = np.mgrid[0:canvas_side, 0:canvas_side].astype(np.float32) / canvas_side
    angle = rng.uniform(0, 2 * np.pi)
    grad = (np.cos(angle) * gx + np.sin(angle) * gy) * rng.uniform(-30, 30)
    bg = bg + grad[..., None] + rng.normal(0, 3, bg.shape)

    oy = int(rng.integers(0, canvas_side - h + 1))
    ox = int(rng.integers(0, canvas_side - w + 1))
    alpha = cv2.GaussianBlur(m, (3, 3), 0).astype(np.float32)[..., None] / 255.0
    region = bg[oy:oy + h, ox:ox + w]
    bg[oy:oy + h, ox:ox + w] = alpha * img.astype(np.float32) + (1 - alpha) * region

    # Balance de blancos, brillo y contraste.
    bg *= rng.uniform(0.93, 1.07, 3)
    bg = (bg - 128) * rng.uniform(0.85, 1.15) + 128 + rng.uniform(-20, 20)
    out = np.clip(bg, 0, 255).astype(np.uint8)
    if rng.random() < 0.4:
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.3, 0.9))
    q = int(rng.integers(60, 96))
    ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR) if ok else out


def add_blemishes(img: np.ndarray, mask: np.ndarray, rng: np.random.Generator, drop: float | None = None,
                  n: int | None = None) -> tuple[np.ndarray, np.ndarray, float]:
    """Pinta 1–3 manchas irregulares dentro del objeto.

    ``drop`` es el oscurecimiento en la escala L de OpenCV (0–255): ~25 es una
    mancha leve apenas visible, ~60 una mancha marrón oscura evidente.
    Devuelve (imagen, máscara verdad, drop usado).
    """
    drop = float(drop if drop is not None else rng.uniform(20, 70))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    truth = np.zeros(mask.shape, np.uint8)
    inner = cv2.erode(mask, np.ones((9, 9), np.uint8))
    ys, xs = np.nonzero(inner)
    if len(ys) == 0:
        return img, truth, drop
    obj_area = np.count_nonzero(mask)
    for _ in range(n or int(rng.integers(1, 4))):
        i = int(rng.integers(len(ys)))
        cy, cx = int(ys[i]), int(xs[i])
        r = np.sqrt(obj_area * rng.uniform(0.01, 0.06) / np.pi)
        blob = np.zeros(mask.shape, np.uint8)
        pts = [(cx + r * rng.uniform(0.6, 1.3) * np.cos(t) * rng.uniform(0.8, 1.4), cy + r * rng.uniform(0.6, 1.3) * np.sin(t))
               for t in np.linspace(0, 2 * np.pi, 14, endpoint=False)]
        cv2.fillPoly(blob, [np.array(pts, np.int32)], 255)
        blob = cv2.bitwise_and(blob, inner)
        if not blob.any():
            continue
        soft = cv2.GaussianBlur(blob, (0, 0), max(1.0, r * 0.15)).astype(np.float32) / 255.0
        texture = rng.normal(1.0, 0.12, soft.shape).astype(np.float32)
        lab[..., 0] -= drop * soft * texture
        # Hacia marrón: menos croma roja/verde, algo de amarillo.
        lab[..., 1] = lab[..., 1] + (138 - lab[..., 1]) * soft * 0.5
        lab[..., 2] = lab[..., 2] + (150 - lab[..., 2]) * soft * 0.4
        truth = cv2.bitwise_or(truth, blob)
    out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    return out, truth, drop
