"""Operaciones sobre lotes: alta, edición controlada, transiciones y decisiones.

Toda modificación deja un evento en ``lot_events`` (trazabilidad).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Area, Decision, Lot, LotEvent, Merchant, Product, utcnow
from .status import ACTIONS, DESTINATIONS, STATUSES


class DomainError(ValueError):
    """Error de negocio con mensaje para el usuario (HTTP 400/409)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


EDITABLE_FIELDS = {
    "merchant_id": "Comerciante", "area_id": "Área", "origin": "Procedencia", "quantity": "Cantidad",
    "quantity_unit": "Unidad", "weight_kg": "Peso (kg)", "observations": "Observaciones", "product_id": "Producto",
}


def add_event(db: Session, lot: Lot, type_: str, title: str, *, detail: str | None = None, actor: str | None = None,
              from_status: str | None = None, to_status: str | None = None, payload: dict | None = None,
              at: datetime | None = None) -> LotEvent:
    ev = LotEvent(lot=lot, type=type_, title=title, detail=detail, actor=actor, from_status=from_status,
                  to_status=to_status, payload=payload or {}, created_at=at or utcnow())
    db.add(ev)
    return ev


def next_code(db: Session, *, demo: bool, at: datetime | None = None) -> str:
    prefix = "MC-D-" if demo else f"MC-{(at or utcnow()).year}-"
    last = db.scalar(select(func.max(Lot.code)).where(Lot.code.like(f"{prefix}%")))
    n = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{n:04d}"


def _get(db: Session, model, id_: int, label: str):
    obj = db.get(model, id_)
    if obj is None:
        raise DomainError(f"{label} no existe.")
    return obj


def create_lot(db: Session, data: dict, *, actor: str | None, at: datetime | None = None, is_demo: bool = False,
               code: str | None = None) -> Lot:
    product = _get(db, Product, data["product_id"], "El producto")
    _get(db, Merchant, data["merchant_id"], "El comerciante")
    _get(db, Area, data["area_id"], "El área")
    if not product.active:
        raise DomainError("El producto no está activo.")
    weight = data.get("weight_kg")
    if weight is not None and weight <= 0:
        raise DomainError("El peso debe ser mayor que cero.")
    at = at or utcnow()
    lot = Lot(
        code=code or next_code(db, demo=is_demo, at=at), product_id=product.id, merchant_id=data["merchant_id"],
        area_id=data["area_id"], origin=(data.get("origin") or None), quantity=data.get("quantity"),
        quantity_unit=data.get("quantity_unit") or "cajas", weight_kg=weight, observations=(data.get("observations") or None),
        status="registrado", is_demo=is_demo, registered_by=actor, created_at=at, updated_at=at,
    )
    db.add(lot)
    db.flush()
    add_event(db, lot, "creado", "Lote registrado", actor=actor, to_status="registrado", at=at,
              detail=f"{product.name}" + (f" · {weight:g} kg" if weight else " · peso pendiente"),
              payload={"weight_kg": weight})
    return lot


def update_lot(db: Session, lot: Lot, changes: dict, *, actor: str, reason: str | None = None, at: datetime | None = None) -> Lot:
    """Edición controlada: no se edita un lote cerrado y el producto solo cambia antes de inspeccionar."""
    if lot.status == "cerrado":
        raise DomainError("El lote está cerrado: no se puede editar.", 409)
    diff = {}
    for field, value in changes.items():
        if field not in EDITABLE_FIELDS:
            continue
        if field == "product_id" and lot.inspections:
            raise DomainError("No se puede cambiar el producto de un lote que ya tiene inspecciones.", 409)
        if field == "weight_kg" and value is not None and value <= 0:
            raise DomainError("El peso debe ser mayor que cero.")
        if field in {"merchant_id", "area_id", "product_id"}:
            _get(db, {"merchant_id": Merchant, "area_id": Area, "product_id": Product}[field], value, EDITABLE_FIELDS[field])
        if isinstance(value, str):
            value = value.strip() or None
        old = getattr(lot, field)
        if old != value:
            diff[field] = {"antes": old, "despues": value}
            setattr(lot, field, value)
    if not diff:
        return lot
    at = at or utcnow()
    lot.updated_at = at
    only_weight = set(diff) == {"weight_kg"}
    labels = ", ".join(EDITABLE_FIELDS[f] for f in diff)
    add_event(db, lot, "peso" if only_weight else "editado",
              f"Peso registrado: {lot.weight_kg:g} kg" if only_weight and lot.weight_kg else f"Datos editados: {labels}",
              detail=reason, actor=actor, payload={"cambios": diff}, at=at)
    return lot


def transition(db: Session, lot: Lot, to_status: str, *, actor: str | None, title: str | None = None,
               detail: str | None = None, at: datetime | None = None) -> None:
    if to_status not in STATUSES:
        raise DomainError(f"Estado desconocido: {to_status}")
    if lot.status == to_status:
        return
    at = at or utcnow()
    add_event(db, lot, "estado", title or f"Estado: {STATUSES[to_status]}", detail=detail, actor=actor,
              from_status=lot.status, to_status=to_status, at=at)
    lot.status = to_status
    lot.updated_at = at
    if to_status == "cerrado":
        lot.closed_at = at


def apply_decision(db: Session, lot: Lot, action_code: str, *, actor: str, role: str, notes: str | None = None,
                   kg: float | None = None, confirm: bool = False, at: datetime | None = None, is_demo: bool = False) -> Decision:
    action = ACTIONS.get(action_code)
    if action is None:
        raise DomainError("Acción desconocida.")
    if not actor or not actor.strip():
        raise DomainError("Indique el nombre de la persona responsable de la decisión.")
    if not role or not role.strip():
        raise DomainError("Indique el rol de la persona responsable.")
    if lot.status not in action.from_statuses:
        raise DomainError(f"No se puede «{action.label}» desde el estado «{STATUSES[lot.status]}».", 409)
    if action.authorized_roles and role not in action.authorized_roles:
        raise DomainError(f"«{action.label}» solo puede registrarlo: {', '.join(action.authorized_roles)}.", 403)
    if action.requires_confirmation and not confirm:
        raise DomainError("Debe confirmar que la evaluación de aptitud fue realizada por personal autorizado.")
    if action.requires_kg:
        if lot.weight_kg is None:
            raise DomainError("Registre el peso del lote antes de cerrar.")
        if kg is None or kg <= 0:
            raise DomainError("Indique los kilogramos de esta decisión.")
        if kg > lot.weight_kg + 1e-9:
            raise DomainError(f"Los kilogramos ({kg:g}) no pueden superar el peso del lote ({lot.weight_kg:g} kg).")

    at = at or utcnow()
    latest = lot.inspections[-1] if lot.inspections else None
    rec = (latest.recommendation or {}) if latest else {}
    decision = Decision(
        lot=lot, inspection_id=latest.id if latest else None, action=action.code,
        recommendation_code=rec.get("code"), followed_recommendation=(action.code in rec.get("suggested_actions", [])) if rec else None,
        actor=actor.strip(), role=role.strip(), notes=(notes or None), kg=kg if action.requires_kg else None,
        from_status=lot.status, to_status=action.to_status, is_demo=is_demo, created_at=at,
    )
    db.add(decision)
    if lot.decided_at is None:
        lot.decided_at = at
    if action.destination:
        lot.destination = action.destination
        if action.destination == "residuos":
            lot.waste_kg = kg
        else:
            lot.recovered_kg = kg

    detail_parts = [f"{role}"]
    if kg:
        detail_parts.append(f"{kg:g} kg")
    if notes:
        detail_parts.append(notes)
    add_event(db, lot, "decision", f"Decisión humana: {action.label}", detail=" · ".join(detail_parts), actor=actor.strip(),
              from_status=lot.status, to_status=action.to_status, at=at,
              payload={"accion": action.code, "kg": kg, "recomendacion": rec.get("code"),
                       "siguio_recomendacion": decision.followed_recommendation,
                       "destino": DESTINATIONS.get(action.destination) if action.destination else None})
    transition(db, lot, action.to_status, actor=actor.strip(), at=at,
               title=f"Estado: {STATUSES[action.to_status]}" + (f" ({DESTINATIONS[action.destination]})" if action.destination else ""))
    return decision
