"""Validación de calidad de imagen.

Cada verificación devuelve ``ok``, ``advertencia`` o ``error`` con su valor
medido y el umbral usado, para que la interfaz pueda explicar el motivo.
Los umbrales de nitidez se calibraron con imágenes de Fruits-360 desenfocadas
artificialmente (ver ``backend/ml/train.py`` y ``docs/dataset-y-validacion.md``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .segmentation import Segmentation

MIN_SIDE_ERROR = 64
MIN_SIDE_WARN = 200
# Nitidez: varianza del Laplaciano normalizada por el contraste del objeto.
SHARPNESS_ERROR = 0.10
SHARPNESS_WARN = 0.30
DARK_ERROR = 35.0         # luminosidad media del producto (0–255)
CLIPPED_ERROR = 0.30      # fracción de píxeles del producto saturados
COVERAGE_ERROR = 0.01
COVERAGE_WARN_HIGH = 0.85
BORDER_TOUCH_WARN = 0.25


@dataclass
class Check:
    code: str
    label: str
    status: str  # ok | advertencia | error
    value: float | None
    threshold: str
    message: str


def sharpness(gray: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Varianza del Laplaciano / varianza de intensidad, sobre el recorte del objeto.

    Se mide sin ampliar la imagen (ampliar la haría parecer borrosa) y reduciendo
    a 256 px como máximo para que el valor no dependa de la resolución.
    """
    if mask is not None and np.count_nonzero(mask):
        ys, xs = np.nonzero(mask)
        pad = 4
        y0, y1 = max(0, ys.min() - pad), min(gray.shape[0], ys.max() + pad)
        x0, x1 = max(0, xs.min() - pad), min(gray.shape[1], xs.max() + pad)
        gray = gray[y0:y1, x0:x1]
    scale = 256 / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    g = gray.astype(np.float32)
    lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
    contrast = float(g.var()) + 1e-6
    return float(lap.var() / contrast)


def assess(bgr: np.ndarray, seg: Segmentation) -> list[Check]:
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    checks: list[Check] = []

    side = min(h, w)
    checks.append(Check(
        "resolucion", "Resolución",
        "error" if side < MIN_SIDE_ERROR else "advertencia" if side < MIN_SIDE_WARN else "ok",
        float(side), f"mínimo {MIN_SIDE_ERROR} px (recomendado ≥ {MIN_SIDE_WARN} px)",
        f"Lado menor de {side} px." + (" Use una foto de mayor resolución." if side < MIN_SIDE_WARN else ""),
    ))

    has_object = seg.bbox is not None and seg.coverage >= COVERAGE_ERROR
    if not has_object:
        checks.append(Check(
            "cobertura", "Producto visible", "error", round(seg.coverage, 4), f"≥ {COVERAGE_ERROR:.0%} de la imagen",
            "No se pudo separar el producto del fondo. Fotografíe el producto centrado sobre una superficie uniforme.",
        ))
        return checks

    cov_status = "advertencia" if seg.coverage > COVERAGE_WARN_HIGH else "ok"
    checks.append(Check(
        "cobertura", "Producto visible", cov_status, round(seg.coverage, 4),
        f"{COVERAGE_ERROR:.0%}–{COVERAGE_WARN_HIGH:.0%} de la imagen",
        f"El producto ocupa {seg.coverage:.0%} de la imagen."
        + (" Ocupa casi todo el encuadre: el fondo no se puede estimar bien." if cov_status != "ok" else ""),
    ))

    touch_status = "advertencia" if seg.border_touch > BORDER_TOUCH_WARN else "ok"
    checks.append(Check(
        "encuadre", "Encuadre", touch_status, round(seg.border_touch, 3), f"≤ {BORDER_TOUCH_WARN:.0%} del borde",
        "El producto está cortado por los bordes de la foto." if touch_status != "ok" else "El producto está dentro del encuadre.",
    ))

    obj = gray[seg.main_mask > 0]
    mean_l = float(obj.mean())
    clipped = float(np.mean(obj >= 250))
    if mean_l < DARK_ERROR:
        exp_status, exp_msg = "error", "La imagen está demasiado oscura."
    elif clipped > CLIPPED_ERROR:
        exp_status, exp_msg = "error", "Hay reflejos o sobreexposición en buena parte del producto."
    else:
        exp_status, exp_msg = "ok", "Exposición adecuada."
    checks.append(Check(
        "exposicion", "Exposición", exp_status, round(mean_l, 1),
        f"brillo medio ≥ {DARK_ERROR:.0f}; saturados ≤ {CLIPPED_ERROR:.0%}", exp_msg,
    ))

    sharp = sharpness(gray, seg.main_mask)
    sh_status = "error" if sharp < SHARPNESS_ERROR else "advertencia" if sharp < SHARPNESS_WARN else "ok"
    checks.append(Check(
        "nitidez", "Nitidez", sh_status, round(sharp, 4), f"≥ {SHARPNESS_ERROR} (recomendado ≥ {SHARPNESS_WARN})",
        {"ok": "Imagen nítida.", "advertencia": "Imagen algo desenfocada.", "error": "Imagen desenfocada o movida."}[sh_status],
    ))
    return checks


def summarize(checks: list[Check]) -> str:
    if any(c.status == "error" for c in checks):
        return "insuficiente"
    if any(c.status == "advertencia" for c in checks):
        return "aceptable"
    return "buena"


def to_dicts(checks: list[Check]) -> list[dict]:
    return [asdict(c) for c in checks]
