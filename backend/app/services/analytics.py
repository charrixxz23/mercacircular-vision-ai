"""Indicadores del dashboard y reportes. Todo se calcula desde la base de datos.

Definiciones (para no mezclar conceptos):
- Volumen registrado: suma del peso de los lotes de excedentes registrados.
- Producto observado: kg de lotes cuya inspección marcó al menos una incidencia.
- Recuperado (confirmado): kg confirmados por una persona como donación o comercialización.
- Merma confirmada: kg confirmados como entregados a gestión de residuos.
Un lote sin decisión de cierre no cuenta como recuperado ni como merma.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Decision, Inspection, Lot, Product, utcnow
from .status import DESTINATIONS, STATUSES

INCIDENT_LABELS = {
    "manchas_oscuras": "Indicios de deterioro (manchas)",
    "calidad_imagen": "Imagen insuficiente",
    "producto_no_coincide": "Producto no coincide",
    "identificacion_incierta": "Identificación incierta",
}
PENDING = {"registrado", "pendiente_inspeccion"}


def _lots(db: Session, start: datetime | None = None, end: datetime | None = None) -> list[Lot]:
    q = select(Lot).options(selectinload(Lot.inspections), selectinload(Lot.decisions))
    if start:
        q = q.where(Lot.created_at >= start)
    if end:
        q = q.where(Lot.created_at < end)
    return list(db.scalars(q).unique())


def _r(x: float) -> float:
    return round(float(x), 1)


def _lot_incidents(lot: Lot) -> set[str]:
    return {i for insp in lot.inspections for i in (insp.incidents or [])}


def _hours(a: datetime | None, b: datetime | None) -> float | None:
    return (b - a).total_seconds() / 3600 if a and b else None


def _avg(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def period_metrics(lots: list[Lot], decisions: list[Decision], inspections: list[Inspection]) -> dict:
    kg_by_product: dict[str, float] = defaultdict(float)
    count_by_product: Counter = Counter()
    for lot in lots:
        count_by_product[lot.product.name] += 1
        kg_by_product[lot.product.name] += lot.weight_kg or 0
    closing = [d for d in decisions if d.action in {"confirmar_donacion", "confirmar_comercializacion", "confirmar_residuos"}]
    kg_dest = defaultdict(float)
    for d in closing:
        kg_dest[{"confirmar_donacion": "donacion", "confirmar_comercializacion": "comercializado", "confirmar_residuos": "residuos"}[d.action]] += d.kg or 0
    incidents = Counter(i for insp in inspections for i in (insp.incidents or []))
    observed = sum((lot.weight_kg or 0) for lot in lots if _lot_incidents(lot))
    return {
        "lotes_registrados": len(lots),
        "kg_registrados": _r(sum(kg_by_product.values())),
        "kg_sin_peso": sum(1 for lot in lots if lot.weight_kg is None),
        "kg_observados": _r(observed),
        "kg_por_producto": {k: _r(v) for k, v in sorted(kg_by_product.items())},
        "lotes_por_producto": dict(sorted(count_by_product.items())),
        "inspecciones": len(inspections),
        "inspecciones_ia": sum(1 for i in inspections if i.mode == "ia"),
        "incidencias": {INCIDENT_LABELS[k]: incidents.get(k, 0) for k in INCIDENT_LABELS},
        "kg_destino_confirmado": {DESTINATIONS[k]: _r(kg_dest.get(k, 0)) for k in DESTINATIONS},
        "kg_recuperado_donacion": _r(kg_dest.get("donacion", 0)),
        "kg_recuperado_comercial": _r(kg_dest.get("comercializado", 0)),
        "kg_merma_confirmada": _r(kg_dest.get("residuos", 0)),
        "tiempos_horas": {
            "registro_a_inspeccion": _avg(_hours(lot.created_at, lot.inspected_at) for lot in lots),
            "inspeccion_a_decision": _avg(_hours(lot.inspected_at, lot.decided_at) for lot in lots),
            "registro_a_cierre": _avg(_hours(lot.created_at, lot.closed_at) for lot in lots),
        },
        "decisiones": len(decisions),
        "decisiones_siguen_recomendacion": sum(1 for d in decisions if d.followed_recommendation),
    }


def dashboard(db: Session, weeks: int = 12, now: datetime | None = None) -> dict:
    now = now or utcnow()
    lots = _lots(db)
    status_counts = Counter(lot.status for lot in lots)
    inspections = [i for lot in lots for i in lot.inspections]
    decisions = [d for lot in lots for d in lot.decisions]
    pm = period_metrics(lots, decisions, inspections)
    products = list(db.scalars(select(Product).order_by(Product.id)))

    # Tendencia semanal (lunes a domingo)
    start_week = (now - timedelta(days=now.weekday())).date() - timedelta(weeks=weeks - 1)
    buckets = [start_week + timedelta(weeks=i) for i in range(weeks)]

    def week_of(dt: datetime) -> date | None:
        wk = (dt - timedelta(days=dt.weekday())).date()
        return wk if wk >= start_week else None

    trend = {wk: {"semana": wk.isoformat(), "kg_registrados": 0.0, "kg_donacion": 0.0, "kg_comercial": 0.0, "kg_residuos": 0.0,
                  "lotes": 0, "incidencias": 0} for wk in buckets}
    for lot in lots:
        wk = week_of(lot.created_at)
        if wk in trend:
            trend[wk]["kg_registrados"] += lot.weight_kg or 0
            trend[wk]["lotes"] += 1
    for d in decisions:
        wk = week_of(d.created_at)
        if wk in trend and d.kg:
            key = {"confirmar_donacion": "kg_donacion", "confirmar_comercializacion": "kg_comercial", "confirmar_residuos": "kg_residuos"}.get(d.action)
            if key:
                trend[wk][key] += d.kg
    for i in inspections:
        wk = week_of(i.created_at)
        if wk in trend and i.incidents:
            trend[wk]["incidencias"] += 1
    trend_list = [{k: (_r(v) if isinstance(v, float) else v) for k, v in row.items()} for row in trend.values()]

    recent = sorted(inspections, key=lambda i: i.created_at, reverse=True)[:8]
    lot_by_id = {lot.id: lot for lot in lots}
    return {
        "generado": now.isoformat(timespec="seconds") + "Z",
        "kpis": {
            "lotes_registrados": len(lots),
            "kg_registrados": pm["kg_registrados"],
            "pendientes_inspeccion": sum(status_counts[s] for s in PENDING),
            "en_evaluacion_donacion": status_counts["evaluacion_donacion"],
            "kg_donacion_confirmada": pm["kg_recuperado_donacion"],
            "en_gestion_residuos": status_counts["gestion_residuos"],
            "kg_residuos_confirmados": pm["kg_merma_confirmada"],
            "kg_recuperado_comercial": pm["kg_recuperado_comercial"],
            "kg_observados": pm["kg_observados"],
            "lotes_demo": sum(1 for lot in lots if lot.is_demo),
            "lotes_reales": sum(1 for lot in lots if not lot.is_demo),
        },
        "por_estado": [{"estado": k, "etiqueta": v, "lotes": status_counts.get(k, 0)} for k, v in STATUSES.items()],
        "por_producto": [{"producto": p.name, "codigo": p.code, "color": p.color, "lotes": pm["lotes_por_producto"].get(p.name, 0),
                          "kg": pm["kg_por_producto"].get(p.name, 0.0)} for p in products],
        "tendencia_semanal": trend_list,
        "incidencias": [{"categoria": k, "total": v} for k, v in pm["incidencias"].items()],
        "destinos": [{"destino": k, "kg": v} for k, v in pm["kg_destino_confirmado"].items()],
        "historial_analisis": [{
            "id": i.id, "lote": lot_by_id[i.lot_id].code, "producto": lot_by_id[i.lot_id].product.name, "modo": i.mode,
            "fecha": i.created_at.isoformat(timespec="seconds") + "Z", "recomendacion": (i.recommendation or {}).get("title"),
            "regiones": i.anomaly_count, "calidad": i.quality_summary, "demo": i.is_demo,
        } for i in recent],
    }


def report(db: Session, start: date, end: date) -> dict:
    """Métricas del período [start, end] y del período anterior de igual duración."""
    if end < start:
        raise ValueError("La fecha final debe ser posterior a la inicial.")
    days = (end - start).days + 1
    s, e = datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())
    ps, pe = s - timedelta(days=days), s

    def collect(a: datetime, b: datetime) -> dict:
        lots = _lots(db, a, b)
        insps = list(db.scalars(select(Inspection).where(Inspection.created_at >= a, Inspection.created_at < b)))
        decs = list(db.scalars(select(Decision).where(Decision.created_at >= a, Decision.created_at < b)))
        return period_metrics(lots, decs, insps)

    current, previous = collect(s, e), collect(ps, pe)
    pending = list(db.scalars(select(Lot).where(Lot.status.in_(PENDING)).order_by(Lot.created_at)))

    def delta(key: str):
        a, b = current[key], previous[key]
        return {"actual": a, "anterior": b, "variacion_pct": round(100 * (a - b) / b, 1) if b else None}

    return {
        "periodo": {"desde": start.isoformat(), "hasta": end.isoformat(), "dias": days},
        "periodo_anterior": {"desde": ps.date().isoformat(), "hasta": (pe - timedelta(days=1)).date().isoformat()},
        "actual": current,
        "anterior": previous,
        "comparacion": {k: delta(k) for k in ("lotes_registrados", "kg_registrados", "kg_observados", "kg_recuperado_donacion",
                                              "kg_recuperado_comercial", "kg_merma_confirmada", "inspecciones")},
        "lotes_pendientes": [{"lote": lot.code, "producto": lot.product.name, "estado": STATUSES[lot.status],
                              "registrado": lot.created_at.isoformat(timespec="minutes") + "Z", "kg": lot.weight_kg,
                              "demo": lot.is_demo} for lot in pending],
        "definiciones": {
            "kg_registrados": "Peso de los lotes de excedentes registrados en el período (volumen de entrada al sistema).",
            "kg_observados": "Peso de los lotes con al menos una incidencia en su inspección. No es merma.",
            "kg_recuperado_donacion": "Kg confirmados por personal autorizado como donación.",
            "kg_recuperado_comercial": "Kg confirmados por un responsable como comercializados tras revisión.",
            "kg_merma_confirmada": "Kg confirmados como entregados a gestión de residuos.",
        },
    }
