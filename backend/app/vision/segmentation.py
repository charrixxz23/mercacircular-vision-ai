"""Segmentación producto / fondo.

Supuesto de operación (documentado como limitación): el producto se fotografía
sobre una superficie relativamente uniforme (bandeja, mesa, papel) y no toca
todos los bordes de la imagen. El color del fondo se estima con los píxeles del
borde y se marca como producto todo lo que se aleja de ese color.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Segmentation:
    mask: np.ndarray            # uint8 0/255, mismo tamaño que la imagen
    main_mask: np.ndarray       # solo el componente más grande
    bbox: tuple[int, int, int, int] | None  # x, y, w, h del componente principal
    coverage: float             # área de producto / área de imagen
    components: int             # objetos relevantes encontrados
    border_touch: float         # fracción del perímetro de la imagen ocupada por producto
    background_uniformity: float  # dispersión del color del borde (menor = más uniforme)


def _border_pixels(lab: np.ndarray, band: int) -> np.ndarray:
    top = lab[:band].reshape(-1, 3)
    bottom = lab[-band:].reshape(-1, 3)
    left = lab[band:-band, :band].reshape(-1, 3)
    right = lab[band:-band, -band:].reshape(-1, 3)
    return np.concatenate([top, bottom, left, right]).astype(np.float32)


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """Rellena huecos interiores. Se agrega un marco de 1 px para que el relleno
    del fondo funcione aunque el objeto toque las esquinas de la imagen."""
    padded = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    h, w = padded.shape
    flood = padded.copy()
    cv2.floodFill(flood, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    holes = cv2.bitwise_not(flood)[1:-1, 1:-1]
    return cv2.bitwise_or(mask, holes)


def segment(bgr: np.ndarray) -> Segmentation:
    h, w = bgr.shape[:2]
    band = max(2, round(min(h, w) * 0.04))
    blurred = cv2.GaussianBlur(bgr, (5, 5), 0)
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB).astype(np.float32)

    border = _border_pixels(lab, band)
    # Fondo con hasta 3 tonos (sombras, gradientes): k-means sobre el borde.
    k = 3 if len(border) >= 30 else 1
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(border, k, None, criteria, 2, cv2.KMEANS_PP_CENTERS)
    # Ignorar centros con muy pocos píxeles (probablemente producto que toca el borde).
    counts = np.bincount(labels.ravel(), minlength=k)
    centers = centers[counts >= 0.08 * len(border)]
    uniformity = float(np.mean(np.std(border, axis=0)))

    # Distancia de cada píxel al color de fondo más cercano (ΔE aproximado).
    flat = lab.reshape(-1, 1, 3)
    dist = np.min(np.linalg.norm(flat - centers.reshape(1, -1, 3), axis=2), axis=1).reshape(h, w)

    # Umbral: Otsu sobre la distancia, con un piso para fondos muy uniformes.
    d8 = np.clip(dist * 2, 0, 255).astype(np.uint8)
    otsu, _ = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = max(otsu / 2.0, 14.0)
    mask = (dist > thr).astype(np.uint8) * 255

    k_size = max(3, (min(h, w) // 60) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = fill_holes(mask)

    n, cc, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        empty = np.zeros_like(mask)
        return Segmentation(empty, empty, None, 0.0, 0, 0.0, uniformity)

    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = int(np.argmax(areas)) + 1
    min_area = max(0.2 * areas.max(), 0.002 * h * w)
    keep = [i + 1 for i, a in enumerate(areas) if a >= min_area]
    clean = np.isin(cc, keep).astype(np.uint8) * 255
    main = (cc == largest).astype(np.uint8) * 255
    x, y, bw, bh = (int(v) for v in stats[largest, :4])

    perimeter = np.concatenate([clean[0], clean[-1], clean[:, 0], clean[:, -1]])
    return Segmentation(
        mask=clean,
        main_mask=main,
        bbox=(x, y, bw, bh),
        coverage=float(np.count_nonzero(clean)) / (h * w),
        components=len(keep),
        border_touch=float(np.count_nonzero(perimeter)) / len(perimeter),
        background_uniformity=uniformity,
    )
