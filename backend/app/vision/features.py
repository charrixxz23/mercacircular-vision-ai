"""Extracción de características (63 valores) del producto segmentado.

- Color: histograma de tono (24), saturación (8) y valor (8) + media y desviación Lab (6).
- Forma: relación de aspecto, solidez, circularidad, extensión, excentricidad (5).
- Textura: histograma LBP uniforme 8 vecinos (10) + gradiente medio y desviación (2).

El recorte se normaliza a 96 px de lado mayor para que las características no
dependan de la distancia de la cámara.
"""

from __future__ import annotations

import cv2
import numpy as np

SIZE = 96
FEATURE_NAMES: list[str] = (
    [f"hue_{i}" for i in range(24)]
    + [f"sat_{i}" for i in range(8)]
    + [f"val_{i}" for i in range(8)]
    + ["L_mean", "a_mean", "b_mean", "L_std", "a_std", "b_std"]
    + ["aspect", "solidity", "circularity", "extent", "eccentricity"]
    + [f"lbp_{i}" for i in range(10)]
    + ["grad_mean", "grad_std"]
)

# Tabla LBP "uniforme": 58 patrones uniformes → su número de unos (0..8), resto → 9.
_LBP_TABLE = np.full(256, 9, np.uint8)
for _code in range(256):
    bits = [(_code >> i) & 1 for i in range(8)]
    transitions = sum(bits[i] != bits[(i + 1) % 8] for i in range(8))
    if transitions <= 2:
        _LBP_TABLE[_code] = sum(bits)


def _crop(bgr: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    img, m = bgr[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    scale = SIZE / max(img.shape[:2])
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)
    m = cv2.resize(m, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    return img, m


def _lbp(gray: np.ndarray) -> np.ndarray:
    g = gray.astype(np.int16)
    c = g[1:-1, 1:-1]
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    code = np.zeros_like(c, dtype=np.uint8)
    for bit, (dy, dx) in enumerate(offsets):
        nb = g[1 + dy:g.shape[0] - 1 + dy, 1 + dx:g.shape[1] - 1 + dx]
        code |= ((nb >= c).astype(np.uint8) << bit)
    return _LBP_TABLE[code]


def _shape(mask: np.ndarray) -> list[float]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    perim = cv2.arcLength(cnt, True) or 1.0
    hull_area = cv2.contourArea(cv2.convexHull(cnt)) or 1.0
    (_, _), (rw, rh), _ = cv2.minAreaRect(cnt)
    long_side, short_side = max(rw, rh, 1e-6), max(min(rw, rh), 1e-6)
    x, y, w, h = cv2.boundingRect(cnt)
    ecc = 0.0
    if len(cnt) >= 5:
        (_, _), axes, _ = cv2.fitEllipse(cnt)
        a, b = max(axes) / 2, min(axes) / 2
        ecc = float(np.sqrt(max(0.0, 1 - (b * b) / (a * a)))) if a > 0 else 0.0
    return [
        long_side / short_side,
        area / hull_area,
        4 * np.pi * area / (perim * perim),
        area / max(w * h, 1),
        ecc,
    ]


def extract(bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Vector de características del objeto indicado por ``mask`` (uint8 0/255)."""
    img, m = _crop(bgr, mask)
    inside = m > 0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    hue, sat, val = hsv[..., 0][inside], hsv[..., 1][inside], hsv[..., 2][inside]

    # El tono no es fiable en píxeles grises: se pondera por la saturación.
    weights = sat.astype(np.float32) / 255.0
    hue_hist, _ = np.histogram(hue, bins=24, range=(0, 180), weights=weights)
    hue_hist = hue_hist / (weights.sum() + 1e-6)
    sat_hist = np.histogram(sat, bins=8, range=(0, 256))[0] / max(len(sat), 1)
    val_hist = np.histogram(val, bins=8, range=(0, 256))[0] / max(len(val), 1)

    lab_in = lab[inside]
    lab_stats = list(lab_in.mean(axis=0) / 255.0) + list(lab_in.std(axis=0) / 255.0)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lbp = _lbp(gray)
    lbp_mask = inside[1:-1, 1:-1]
    eroded = cv2.erode(m, np.ones((3, 3), np.uint8))[1:-1, 1:-1] > 0  # evitar el contorno
    sel = lbp[eroded] if eroded.any() else lbp[lbp_mask]
    lbp_hist = np.bincount(sel, minlength=10)[:10] / max(len(sel), 1)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    interior = np.pad(eroded, 1)  # misma forma que la imagen, sin el contorno
    grad = np.sqrt(gx * gx + gy * gy)[interior]
    grad_stats = [float(grad.mean()) / 255.0, float(grad.std()) / 255.0] if grad.size else [0.0, 0.0]

    vec = np.concatenate([hue_hist, sat_hist, val_hist, lab_stats, _shape(m), lbp_hist, grad_stats]).astype(np.float64)
    assert vec.shape[0] == len(FEATURE_NAMES)
    return vec
