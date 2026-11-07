"""Conversión de modelos ORM a JSON para la API."""

from __future__ import annotations

from datetime import datetime

from .models import Decision, Inspection, Lot, LotEvent, LotImage
from .services.status import ACTIONS, DESTINATIONS, STATUSES, available_actions


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def media_url(filename: str | None) -> str | None:
    return f"/media/{filename}" if filename else None


def image(img: LotImage) -> dict:
    return {"id": img.id, "url": media_url(img.filename), "source": img.source, "width": img.width, "height": img.height,
            "original_name": img.original_name, "sha256": img.sha256, "created_at": iso(img.created_at)}


def inspection(i: Inspection) -> dict:
    return {
        "id": i.id, "mode": i.mode, "scenario": i.scenario, "model_version": i.model_version,
        "declared_product": i.declared_product, "predicted_product": i.predicted_product, "prediction_score": i.prediction_score,
        "quality_summary": i.quality_summary, "anomaly_count": i.anomaly_count, "affected_pct": i.affected_pct,
        "incidents": i.incidents or [], "result": i.result, "recommendation": i.recommendation,
        "image": image(i.image) if i.image else None, "annotated_url": media_url(i.annotated_filename),
        "processing_ms": i.processing_ms, "performed_by": i.performed_by, "is_demo": i.is_demo, "created_at": iso(i.created_at),
    }


def decision(d: Decision) -> dict:
    return {"id": d.id, "action": d.action, "action_label": ACTIONS[d.action].label if d.action in ACTIONS else d.action,
            "actor": d.actor, "role": d.role, "notes": d.notes, "kg": d.kg, "from_status": d.from_status, "to_status": d.to_status,
            "recommendation_code": d.recommendation_code, "followed_recommendation": d.followed_recommendation,
            "is_demo": d.is_demo, "created_at": iso(d.created_at)}


def event(e: LotEvent) -> dict:
    return {"id": e.id, "type": e.type, "title": e.title, "detail": e.detail, "actor": e.actor, "from_status": e.from_status,
            "to_status": e.to_status, "payload": e.payload, "created_at": iso(e.created_at)}


def lot_summary(lot: Lot) -> dict:
    last = lot.inspections[-1] if lot.inspections else None
    return {
        "code": lot.code, "product": {"id": lot.product.id, "code": lot.product.code, "name": lot.product.name, "color": lot.product.color},
        "merchant": {"id": lot.merchant.id, "name": lot.merchant.name}, "area": {"id": lot.area.id, "name": lot.area.name},
        "origin": lot.origin, "quantity": lot.quantity, "quantity_unit": lot.quantity_unit, "weight_kg": lot.weight_kg,
        "status": lot.status, "status_label": STATUSES[lot.status], "destination": lot.destination,
        "destination_label": DESTINATIONS.get(lot.destination or ""), "recovered_kg": lot.recovered_kg, "waste_kg": lot.waste_kg,
        "is_demo": lot.is_demo, "created_at": iso(lot.created_at), "updated_at": iso(lot.updated_at), "closed_at": iso(lot.closed_at),
        "images": len(lot.images), "inspections": len(lot.inspections),
        "last_recommendation": (last.recommendation or {}).get("title") if last else None,
        "incidents": sorted({x for i in lot.inspections for x in (i.incidents or [])}),
    }


def _current_recommendation(lot: Lot, rec: dict | None) -> dict | None:
    """La recomendación se guarda tal como se emitió; aquí solo se retira la regla
    R07 (peso pendiente) si el peso ya se registró después del análisis."""
    if not rec:
        return None
    if lot.weight_kg is not None:
        rec = {**rec, "reasons": [r for r in rec.get("reasons", []) if r.get("rule") != "R07"]}
    return rec


def lot_detail(lot: Lot) -> dict:
    last = lot.inspections[-1] if lot.inspections else None
    return {
        **lot_summary(lot),
        "observations": lot.observations, "registered_by": lot.registered_by,
        "inspected_at": iso(lot.inspected_at), "decided_at": iso(lot.decided_at),
        "image_list": [image(i) for i in lot.images],
        "inspection_list": [inspection(i) for i in reversed(lot.inspections)],
        "decision_list": [decision(d) for d in reversed(lot.decisions)],
        "timeline": [event(e) for e in lot.events],
        "current_recommendation": _current_recommendation(lot, last.recommendation) if last else None,
        "available_actions": [{"code": a.code, "label": a.label, "description": a.description, "requires_kg": a.requires_kg,
                               "requires_confirmation": a.requires_confirmation, "authorized_roles": list(a.authorized_roles),
                               "suggested": bool(last and a.code in (last.recommendation or {}).get("suggested_actions", []))}
                              for a in available_actions(lot.status)],
        "editable": lot.status != "cerrado",
    }
