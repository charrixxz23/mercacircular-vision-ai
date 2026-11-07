"""Detector heurístico de indicios de deterioro exterior (manchas oscuras).

Qué hace: dentro del producto segmentado busca zonas claramente más oscuras que
su entorno inmediato (golpes, magulladuras, pudrición superficial, manchas).
Cada región que devuelve es una salida real del algoritmo, con su caja y área.

Qué NO hace: no diagnostica enfermedades, no mide frescura interna ni
determina inocuidad. Las manchas naturales (p. ej. el banano maduro, la tierra
en la papa) también se marcan: por eso siempre se pide revisión humana.

Validación: con manchas sintéticas sobre imágenes de prueba (ver
``backend/ml/evaluate_anomalies.py``). No se validó con defectos reales
etiquetados, porque no se dispone de ese conjunto de datos.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Parámetros elegidos con las imágenes de los grupos de entrenamiento (ver metrics.json).
DEFAULT_PARAMS = {
    "delta_l": 18.0,          # oscurecimiento mínimo respecto al entorno (escala L 0–255)
    "min_area_frac": 0.015,   # región mínima: 1.5 % del área del producto
    "erode_frac": 0.04,       # margen interno para ignorar el contorno y sombras de borde
    "green_a_max": 120.0,     # a* (OpenCV) por debajo = verde: pedúnculos y hojas, se ignoran
    "local_k_frac": 0.25,      # ventana del contraste local (fracción del tamaño del producto)
    "local_factor": 0.6,      # el contraste local debe superar local_factor × delta_l
}


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int
    area_pct: float      # % del área del producto
    darkening: float     # oscurecimiento medio respecto al entorno (L, 0–255)


def _shading_model(L: np.ndarray, inner: np.ndarray) -> np.ndarray:
    """Ajuste robusto (2 pasadas) de L ≈ c0 + c1·x + c2·y + c3·x² + c4·xy + c5·y²."""
    ys, xs = np.nonzero(inner)
    h, w = L.shape
    sx, sy = max(w, 1), max(h, 1)

    def design(xv, yv):
        xv = xv / sx
        yv = yv / sy
        return np.stack([np.ones_like(xv), xv, yv, xv * xv, xv * yv, yv * yv], axis=1)

    A = design(xs.astype(np.float64), ys.astype(np.float64))
    target = L[ys, xs].astype(np.float64)
    coef, *_ = np.linalg.lstsq(A, target, rcond=None)
    # Segunda pasada sin los píxeles muy oscuros (posibles manchas) para que no arrastren el ajuste.
    resid = A @ coef - target
    keep = resid < np.percentile(resid, 85)
    if keep.sum() > 12:
        coef, *_ = np.linalg.lstsq(A[keep], target[keep], rcond=None)
    gy, gx = np.mgrid[0:h, 0:w]
    return (design(gx.ravel().astype(np.float64), gy.ravel().astype(np.float64)) @ coef).reshape(h, w).astype(np.float32)


def detect(bgr: np.ndarray, mask: np.ndarray, params: dict | None = None) -> tuple[list[Region], float, np.ndarray]:
    """Devuelve (regiones, fracción del producto afectada, máscara de anomalías)."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    obj_area = int(np.count_nonzero(mask))
    empty = np.zeros_like(mask)
    if obj_area < 50:
        return [], 0.0, empty

    ys, xs = np.nonzero(mask)
    size = max(ys.max() - ys.min(), xs.max() - xs.min()) + 1
    er = max(1, int(round(size * p["erode_frac"])))
    inner = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * er + 1, 2 * er + 1)))
    if not np.count_nonzero(inner):
        return [], 0.0, empty

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    L = lab[..., 0].astype(np.float32)
    a = lab[..., 1].astype(np.float32)

    # 1) Sombreado esperado: superficie polinómica de grado 2 ajustada a la
    #    luminosidad del producto (una fruta iluminada de lado se oscurece de
    #    forma suave; una mancha es un cambio brusco y local).
    expected = _shading_model(L, inner)
    darker_than_shading = (expected - L) > p["delta_l"]

    # 2) Contraste local: además debe ser más oscura que su entorno inmediato.
    fill = float(np.median(L[inner > 0]))
    L_filled = np.where(inner > 0, L, fill).astype(np.uint8)
    k = int(size * p["local_k_frac"]) | 1
    k = min(max(k, 3), 255)
    local = cv2.medianBlur(L_filled, k).astype(np.float32)
    darker_than_local = (local - L) > p["local_factor"] * p["delta_l"]

    not_green = a >= p["green_a_max"]
    cand = (darker_than_shading & darker_than_local & not_green & (inner > 0)).astype(np.uint8) * 255
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cand = cv2.bitwise_and(cand, inner)

    n, cc, stats, _ = cv2.connectedComponentsWithStats(cand, 8)
    min_area = max(6, p["min_area_frac"] * obj_area)
    regions: list[Region] = []
    out = np.zeros_like(mask)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        comp = cc == i
        out[comp] = 255
        x, y, w, h = (int(v) for v in stats[i, :4])
        regions.append(Region(x, y, w, h, round(100 * area / obj_area, 2), round(float((local - L)[comp].mean()), 1)))

    regions.sort(key=lambda r: r.area_pct, reverse=True)
    return regions, float(np.count_nonzero(out)) / obj_area, out
