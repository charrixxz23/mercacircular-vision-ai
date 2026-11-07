"""Pipeline de análisis visual (modo IA real).

    imagen → validación → segmentación → identificación → detección de manchas → resultado

El resultado distingue siempre lo que el sistema midió de lo que NO puede
afirmar, y declara las limitaciones aplicables a ese análisis concreto.
"""

from __future__ import annotations

import time
import cv2
import numpy as np

from . import anomalies, features, quality
from .classifier import ProductClassifier
from .segmentation import segment

WORK_MAX_SIDE = 800

GENERAL_LIMITATIONS = [
    "El clasificador se entrenó con imágenes de laboratorio (Fruits-360, fondo controlado); su desempeño con fotos del mercado no está validado.",
    "La detección de manchas es una heurística de color validada solo con manchas sintéticas; puede marcar manchas naturales, tierra o el pedúnculo.",
    "Solo se analiza la cara visible del producto en la foto; no evalúa el interior ni el resto del lote.",
    "El análisis no certifica inocuidad ni aptitud para consumo: esa decisión corresponde a personal autorizado.",
]

# Colores de dibujo (BGR)
OUTLINE = (128, 160, 20)   # verde azulado: contorno del producto
BOX = (0, 140, 255)        # naranja: regiones marcadas


def decode(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("El archivo no es una imagen válida (use JPG, PNG o WebP).")
    return img


def analyze(bgr: np.ndarray, declared_product: str, classifier: ProductClassifier | None,
            class_sensitivity: dict[str, float] | None = None) -> tuple[dict, np.ndarray]:
    """Devuelve (resultado serializable, imagen anotada BGR)."""
    t0 = time.perf_counter()
    h0, w0 = bgr.shape[:2]
    scale = min(1.0, WORK_MAX_SIDE / max(h0, w0))
    work = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else bgr.copy()

    seg = segment(work)
    checks = quality.assess(work, seg)
    q_summary = quality.summarize(checks)
    observations: list[str] = []
    limitations = list(GENERAL_LIMITATIONS)

    result: dict = {
        "mode": "ia",
        "image": {"width": w0, "height": h0, "analyzed_scale": round(scale, 4)},
        "quality": {"summary": q_summary, "checks": quality.to_dicts(checks)},
        "segmentation": {"coverage": round(seg.coverage, 4), "objects": seg.components,
                         "bbox": _scale_box(seg.bbox, scale) if seg.bbox else None},
        "identification": {"available": False, "declared": declared_product},
        "anomalies": {"available": False, "count": 0, "affected_pct": None, "regions": [],
                      "method": "Heurística de oscurecimiento local sobre modelo de sombreado (OpenCV)"},
    }
    annotated = bgr.copy()

    if seg.bbox is None:
        observations.append("No se encontró un producto separable del fondo; no se realizó identificación ni detección de manchas.")
        result.update(observations=observations, limitations=limitations, processing_ms=_ms(t0))
        return result, annotated

    # Identificación
    if classifier is not None:
        pred = classifier.predict(features.extract(work, seg.main_mask))
        reliable = pred.probability >= classifier.min_confidence
        in_model = declared_product in classifier.classes
        result["identification"] = {
            "available": True, "declared": declared_product, "predicted": pred.label,
            "probability": round(pred.probability, 4), "probabilities": pred.probabilities,
            "min_confidence": classifier.min_confidence, "reliable": reliable,
            "declared_in_model": in_model,
            "matches_declared": pred.label == declared_product if in_model else None,
            "model_version": classifier.version,
            "note": "Probabilidad de una regresión logística; su calibración se midió en prueba (ver ficha del modelo).",
        }
        if not reliable:
            observations.append(f"Identificación incierta: probabilidad {pred.probability:.0%} menor que el umbral {classifier.min_confidence:.0%}.")
        elif not in_model:
            observations.append(f"«{declared_product}» no es una clase del modelo: la identificación solo es orientativa.")
        elif pred.label != declared_product:
            observations.append(f"El modelo sugiere «{pred.label}» y se declaró «{declared_product}».")
        sens = (class_sensitivity or {}).get(declared_product)
        if sens is not None and sens < 0.6:
            limitations.insert(0, f"Para «{declared_product}» el modelo tuvo baja sensibilidad en prueba ({sens:.0%}); confíe en el producto declarado.")
    else:
        result["identification"]["note"] = "Modelo de identificación no disponible; se usa el producto declarado."
        observations.append("No hay modelo de identificación cargado (ver docs/dataset-y-validacion.md para entrenarlo).")

    # Manchas (sobre todos los objetos segmentados)
    regions, frac, _ = anomalies.detect(work, seg.mask)
    result["anomalies"].update({
        "available": True,
        "count": len(regions),
        "affected_pct": round(100 * frac, 2),
        "regions": [{**_scale_box((r.x, r.y, r.w, r.h), scale), "area_pct": r.area_pct, "darkening": r.darkening} for r in regions],
    })
    if regions:
        observations.append(f"Se marcaron {len(regions)} región(es) más oscuras que su entorno ({100 * frac:.1f} % del producto visible).")
    else:
        observations.append("No se marcaron regiones oscuras en la parte visible del producto.")
    if q_summary != "buena":
        observations.append("La calidad de la imagen no es óptima: tome los resultados con cautela.")
    if seg.components > 1:
        observations.append(f"Se detectaron {seg.components} objetos; la identificación usa el más grande.")

    annotated = draw(bgr, seg.mask, scale, result["anomalies"]["regions"])
    result.update(observations=observations, limitations=limitations, processing_ms=_ms(t0))
    return result, annotated


def draw(bgr: np.ndarray, mask_work: np.ndarray, scale: float, regions: list[dict]) -> np.ndarray:
    out = bgr.copy()
    h, w = out.shape[:2]
    mask = cv2.resize(mask_work, (w, h), interpolation=cv2.INTER_NEAREST) if scale < 1 else mask_work
    thick = max(2, round(max(h, w) / 300))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, OUTLINE, thick)
    for i, r in enumerate(regions, 1):
        cv2.rectangle(out, (r["x"], r["y"]), (r["x"] + r["w"], r["y"] + r["h"]), BOX, thick)
        fs = max(0.4, max(h, w) / 900)
        cv2.putText(out, str(i), (r["x"], max(12, r["y"] - 4)), cv2.FONT_HERSHEY_SIMPLEX, fs, BOX, thick)
    return out


def _scale_box(box, scale: float) -> dict:
    x, y, w, h = box
    inv = 1 / scale
    return {"x": int(round(x * inv)), "y": int(round(y * inv)), "w": int(round(w * inv)), "h": int(round(h * inv))}


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


__all__ = ["analyze", "decode", "draw", "GENERAL_LIMITATIONS"]
