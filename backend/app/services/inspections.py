"""Imágenes e inspecciones: almacenamiento seguro y ejecución del análisis."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Inspection, Lot, LotImage, utcnow
from ..vision import pipeline
from ..vision.classifier import ProductClassifier
from . import rules
from .lots import DomainError, add_event, transition

log = logging.getLogger(__name__)
STORE_MAX_SIDE = 1600


@dataclass
class VisionRuntime:
    """Recursos cargados al iniciar: modelo, métricas y escenarios demostrativos."""
    classifier: ProductClassifier | None = None
    model_error: str | None = None
    metrics: dict = field(default_factory=dict)
    class_sensitivity: dict[str, float] = field(default_factory=dict)
    scenarios: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, settings: Settings) -> "VisionRuntime":
        rt = cls()
        try:
            rt.classifier = ProductClassifier.load(settings.model_path)
        except FileNotFoundError:
            rt.model_error = f"No se encontró el modelo en {settings.model_path}."
        except Exception as exc:  # modelo corrupto o incompatible
            rt.model_error = f"No se pudo cargar el modelo: {exc}"
        if rt.model_error:
            log.warning(rt.model_error)
        if settings.metrics_path.exists():
            rt.metrics = json.loads(settings.metrics_path.read_text(encoding="utf-8"))
            per_class = rt.metrics.get("clasificador", {}).get("prueba", {}).get("por_clase", {})
            rt.class_sensitivity = {k: v["sensibilidad"] for k, v in per_class.items()}
        scen_path = settings.demo_data_dir / "scenarios.json"
        if scen_path.exists():
            data = json.loads(scen_path.read_text(encoding="utf-8"))
            rt.scenarios = {s["id"]: s for s in data["escenarios"]}
        return rt


# ─── Imágenes ───────────────────────────────────────────────────────────────

def save_image(db: Session, lot: Lot, data: bytes, *, settings: Settings, original_name: str | None,
               source: str = "upload", actor: str | None = None, at: datetime | None = None) -> LotImage:
    if lot.status == "cerrado":
        raise DomainError("El lote está cerrado: no admite nuevas imágenes.", 409)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise DomainError(f"La imagen supera {settings.max_upload_mb:g} MB.", 413)
    try:
        img = pipeline.decode(data)
    except ValueError as exc:
        raise DomainError(str(exc), 415) from exc

    # Se vuelve a codificar como JPEG: normaliza el formato y elimina metadatos EXIF (p. ej., GPS).
    h, w = img.shape[:2]
    scale = min(1.0, STORE_MAX_SIDE / max(h, w))
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise DomainError("No se pudo procesar la imagen.", 415)
    payload = enc.tobytes()
    rel = Path("lots") / lot.code / f"{uuid.uuid4().hex[:12]}.jpg"
    dest = settings.media_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)

    at = at or utcnow()
    image = LotImage(lot=lot, filename=rel.as_posix(), original_name=(original_name or "")[:200] or None,
                     source=source if source in {"camera", "upload", "sample"} else "upload",
                     width=img.shape[1], height=img.shape[0], sha256=hashlib.sha256(payload).hexdigest(), created_at=at)
    db.add(image)
    db.flush()
    origin = {"camera": "cámara", "upload": "archivo", "sample": "imagen de ejemplo"}[image.source]
    add_event(db, lot, "imagen", "Fotografía agregada", detail=f"Desde {origin} · {image.width}×{image.height} px",
              actor=actor, payload={"image_id": image.id, "filename": image.filename}, at=at)
    if lot.status == "registrado":
        transition(db, lot, "pendiente_inspeccion", actor=actor, at=at)
    return image


def load_image(settings: Settings, image: LotImage) -> np.ndarray:
    data = (settings.media_dir / image.filename).read_bytes()
    return pipeline.decode(data)


# ─── Inspección ─────────────────────────────────────────────────────────────

def incidents_from(result: dict) -> list[str]:
    out = []
    if result.get("quality", {}).get("summary") == "insuficiente":
        out.append("calidad_imagen")
    if (result.get("anomalies", {}).get("count") or 0) > 0:
        out.append("manchas_oscuras")
    ident = result.get("identification", {})
    if ident.get("available"):
        if not ident.get("reliable"):
            out.append("identificacion_incierta")
        elif ident.get("matches_declared") is False:
            out.append("producto_no_coincide")
    return out


def demo_result(scenario: dict, declared: str) -> dict:
    """Resultado de un escenario demostrativo. Nunca incluye regiones ni probabilidades."""
    insufficient = scenario["calidad"] == "insuficiente"
    return {
        "mode": "demo",
        "scenario": {"id": scenario["id"], "title": scenario["titulo"], "description": scenario["descripcion"]},
        "quality": {"summary": scenario["calidad"], "checks": [{
            "code": "escenario", "label": "Calidad (predefinida)", "status": "error" if insufficient else "ok",
            "value": None, "threshold": "—", "message": scenario.get("mensaje_calidad", "Calidad definida por el escenario."),
        }]},
        "identification": {"available": False, "declared": declared,
                           "note": "Modo demostrativo: no se ejecuta identificación automática."},
        "anomalies": {"available": True, "count": scenario["anomalias"]["cantidad"],
                      "affected_pct": scenario["anomalias"].get("porcentaje"), "regions": [],
                      "method": "Escenario predefinido (sin modelo)", "description": scenario["anomalias"]["descripcion"]},
        "observations": [scenario["anomalias"]["descripcion"]],
        "limitations": ["MODO DEMOSTRATIVO: este resultado está escrito de antemano para mostrar el flujo de trabajo. "
                        "No proviene de un modelo de visión artificial y no describe la imagen cargada."],
        "processing_ms": 0,
    }


def run_inspection(db: Session, lot: Lot, *, mode: str, settings: Settings, runtime: VisionRuntime,
                   image: LotImage | None = None, scenario_id: str | None = None, actor: str | None = None,
                   at: datetime | None = None, is_demo: bool = False, demo_override: dict | None = None) -> Inspection:
    if lot.status == "cerrado":
        raise DomainError("El lote está cerrado: no se puede inspeccionar.", 409)
    declared = lot.product.model_label or lot.product.code
    annotated_rel = None

    if mode == "ia":
        if image is None:
            raise DomainError("Para el modo IA debe adjuntar una imagen.")
        bgr = load_image(settings, image)
        result, annotated = pipeline.analyze(bgr, declared, runtime.classifier, runtime.class_sensitivity)
        if result["anomalies"]["regions"] or result.get("segmentation", {}).get("bbox"):
            annotated_rel = Path(image.filename).with_name(Path(image.filename).stem + "_analisis.jpg").as_posix()
            cv2.imwrite(str(settings.media_dir / annotated_rel), annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    elif mode == "demo":
        scenario = demo_override or runtime.scenarios.get(scenario_id or "")
        if scenario is None:
            raise DomainError("Elija un escenario demostrativo válido.")
        result = demo_result(scenario, declared)
        if image is not None:
            result["observations"].append("La imagen se guardó como evidencia, pero NO fue analizada en modo demostrativo.")
    else:
        raise DomainError("Modo desconocido: use 'ia' o 'demo'.")

    rec = rules.recommend(result, lot.weight_kg, runtime.class_sensitivity if mode == "ia" else None).to_dict()
    at = at or utcnow()
    ident = result.get("identification", {})
    insp = Inspection(
        lot=lot, image_id=image.id if image else None, mode=mode, scenario=result.get("scenario", {}).get("id"),
        model_version=ident.get("model_version"), declared_product=declared, predicted_product=ident.get("predicted"),
        prediction_score=ident.get("probability"), quality_summary=result["quality"]["summary"],
        anomaly_count=result["anomalies"]["count"] or 0, affected_pct=result["anomalies"].get("affected_pct"),
        incidents=incidents_from(result), result=result, recommendation=rec, annotated_filename=annotated_rel,
        processing_ms=result.get("processing_ms"), performed_by=actor, is_demo=is_demo, created_at=at,
    )
    db.add(insp)
    db.flush()
    if lot.inspected_at is None:
        lot.inspected_at = at
    mode_label = "IA" if mode == "ia" else "demostrativo"
    add_event(db, lot, "inspeccion", f"Inspección visual ({mode_label})", actor=actor, at=at,
              detail=f"{rec['title']} · {result['anomalies']['count']} región(es) marcada(s) · calidad {result['quality']['summary']}",
              payload={"inspection_id": insp.id, "modo": mode, "recomendacion": rec["code"], "incidencias": insp.incidents})
    if lot.status in {"registrado", "pendiente_inspeccion"}:
        transition(db, lot, "inspeccionado", actor=actor, at=at)
    return insp
