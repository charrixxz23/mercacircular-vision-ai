"""Rutas de la API REST (documentación interactiva en /docs)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from .. import serializers as ser
from ..config import Settings
from ..models import Area, Lot, LotImage, Merchant, Product, utcnow
from ..schemas import DecisionCreate, InspectionCreate, LotCreate, LotUpdate, StatusChange
from ..services import analytics, exports, rules, seed
from ..services import inspections as insp_service
from ..services import lots as lot_service
from ..services.lots import DomainError
from ..services.status import ACTIONS, AUTHORIZED_DONATION_ROLES, DESTINATIONS, ROLES, STATUSES
from ..vision.pipeline import GENERAL_LIMITATIONS

router = APIRouter(prefix="/api")


def get_db(request: Request):
    yield from request.app.state.db.session()


def settings_of(request: Request) -> Settings:
    return request.app.state.settings


def runtime_of(request: Request) -> insp_service.VisionRuntime:
    return request.app.state.runtime


DB = Annotated[Session, Depends(get_db)]


def _lot(db: Session, code: str) -> Lot:
    lot = db.scalar(select(Lot).where(Lot.code == code).options(
        selectinload(Lot.images), selectinload(Lot.inspections), selectinload(Lot.decisions), selectinload(Lot.events)))
    if lot is None:
        raise HTTPException(404, f"No existe el lote {code}.")
    return lot


def _commit_or_400(db: Session, fn):
    try:
        out = fn()
        db.commit()
        return out
    except DomainError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, str(exc)) from exc


# ─── Sistema ────────────────────────────────────────────────────────────────

@router.get("/health", tags=["sistema"])
def health(request: Request):
    rt = runtime_of(request)
    return {"status": "ok", "model_loaded": rt.classifier is not None, "model_version": rt.classifier.version if rt.classifier else None,
            "model_error": rt.model_error, "time": ser.iso(utcnow())}


@router.get("/catalog", tags=["sistema"])
def catalog(db: DB, request: Request):
    rt = runtime_of(request)
    return {
        "products": [{"id": p.id, "code": p.code, "name": p.name, "color": p.color, "in_model": bool(rt.classifier and (p.model_label in rt.classifier.classes))}
                     for p in db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.id))],
        "merchants": [{"id": m.id, "name": m.name, "is_demo": m.is_demo} for m in db.scalars(select(Merchant).order_by(Merchant.name))],
        "areas": [{"id": a.id, "name": a.name} for a in db.scalars(select(Area).order_by(Area.id))],
        "statuses": [{"code": k, "label": v} for k, v in STATUSES.items()],
        "destinations": [{"code": k, "label": v} for k, v in DESTINATIONS.items()],
        "roles": ROLES, "donation_roles": AUTHORIZED_DONATION_ROLES,
        "actions": [{"code": a.code, "label": a.label, "description": a.description} for a in ACTIONS.values()],
        "scenarios": [{"id": s["id"], "title": s["titulo"], "description": s["descripcion"]} for s in rt.scenarios.values()],
        "incident_labels": analytics.INCIDENT_LABELS,
    }


# ─── Lotes ──────────────────────────────────────────────────────────────────

@router.get("/lots", tags=["lotes"])
def list_lots(db: DB, q: str | None = None, status: str | None = None, product: str | None = None, area_id: int | None = None,
              demo: bool | None = None, desde: date | None = None, hasta: date | None = None,
              limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    query = select(Lot).join(Lot.product).join(Lot.merchant).options(selectinload(Lot.inspections), selectinload(Lot.images))
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Lot.code.ilike(like), Merchant.name.ilike(like), Lot.origin.ilike(like), Lot.observations.ilike(like)))
    if status:
        query = query.where(Lot.status.in_(status.split(",")))
    if product:
        query = query.where(Product.code == product)
    if area_id:
        query = query.where(Lot.area_id == area_id)
    if demo is not None:
        query = query.where(Lot.is_demo.is_(demo))
    if desde:
        query = query.where(Lot.created_at >= desde)
    if hasta:
        query = query.where(Lot.created_at < hasta + timedelta(days=1))
    total = len(db.scalars(query).unique().all())
    rows = db.scalars(query.order_by(Lot.created_at.desc(), Lot.id.desc()).limit(limit).offset(offset)).unique().all()
    return {"total": total, "items": [ser.lot_summary(r) for r in rows]}


@router.post("/lots", status_code=201, tags=["lotes"])
def create_lot(body: LotCreate, db: DB):
    lot = _commit_or_400(db, lambda: lot_service.create_lot(db, body.model_dump(), actor=body.registered_by or "Usuario de la demo"))
    return ser.lot_detail(_lot(db, lot.code))


@router.get("/lots/{code}", tags=["lotes"])
def get_lot(code: str, db: DB):
    return ser.lot_detail(_lot(db, code))


@router.patch("/lots/{code}", tags=["lotes"])
def update_lot(code: str, body: LotUpdate, db: DB):
    lot = _lot(db, code)
    changes = body.model_dump(exclude_unset=True, exclude={"actor", "reason"})
    _commit_or_400(db, lambda: lot_service.update_lot(db, lot, changes, actor=body.actor, reason=body.reason))
    return ser.lot_detail(_lot(db, code))


@router.post("/lots/{code}/status", tags=["lotes"])
def change_status(code: str, body: StatusChange, db: DB):
    """Acciones operativas sin decisión de destino (p. ej. enviar a inspección)."""
    lot = _lot(db, code)
    if body.action != "marcar_pendiente":
        raise HTTPException(400, "Use /decisions para las decisiones de destino.")
    _commit_or_400(db, lambda: lot_service.apply_decision(db, lot, "marcar_pendiente", actor=body.actor, role="Operador(a) de recepción"))
    return ser.lot_detail(_lot(db, code))


@router.post("/lots/{code}/images", status_code=201, tags=["inspección"])
async def upload_image(code: str, request: Request, db: DB, file: UploadFile = File(...),
                       source: str = Form("upload"), actor: str | None = Form(None)):
    lot = _lot(db, code)
    settings = settings_of(request)
    data = await file.read(int(settings.max_upload_mb * 1024 * 1024) + 1)
    img = _commit_or_400(db, lambda: insp_service.save_image(db, lot, data, settings=settings, original_name=file.filename,
                                                             source=source, actor=actor))
    return ser.image(img)


@router.post("/lots/{code}/inspections", status_code=201, tags=["inspección"])
def inspect(code: str, body: InspectionCreate, request: Request, db: DB):
    lot = _lot(db, code)
    image = None
    if body.image_id is not None:
        image = db.get(LotImage, body.image_id)
        if image is None or image.lot_id != lot.id:
            raise HTTPException(404, "La imagen no pertenece a este lote.")
    insp = _commit_or_400(db, lambda: insp_service.run_inspection(
        db, lot, mode=body.mode, image=image, scenario_id=body.scenario_id, actor=body.actor,
        settings=settings_of(request), runtime=runtime_of(request)))
    return ser.inspection(insp)


@router.post("/lots/{code}/decisions", status_code=201, tags=["decisiones"])
def decide(code: str, body: DecisionCreate, db: DB):
    lot = _lot(db, code)
    _commit_or_400(db, lambda: lot_service.apply_decision(db, lot, body.action, actor=body.actor, role=body.role, notes=body.notes,
                                                         kg=body.kg, confirm=body.confirm))
    return ser.lot_detail(_lot(db, code))


@router.get("/lots/{code}/timeline", tags=["trazabilidad"])
def timeline(code: str, db: DB):
    lot = _lot(db, code)
    return {"lot": lot.code, "events": [ser.event(e) for e in lot.events]}


# ─── Dashboard y reportes ───────────────────────────────────────────────────

@router.get("/dashboard", tags=["indicadores"])
def dashboard(db: DB, weeks: int = Query(12, ge=4, le=52)):
    return analytics.dashboard(db, weeks)


def _period(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hasta = hasta or (utcnow() - timedelta(hours=5)).date()  # fecha local de Panamá
    desde = desde or hasta - timedelta(days=27)
    if hasta < desde:
        raise HTTPException(400, "La fecha final debe ser posterior a la inicial.")
    return desde, hasta


@router.get("/reports/summary", tags=["reportes"])
def report_summary(db: DB, desde: date | None = None, hasta: date | None = None):
    return analytics.report(db, *_period(desde, hasta))


def _download(data: bytes, filename: str, media: str) -> Response:
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/reports/summary.csv", tags=["reportes"])
def report_summary_csv(db: DB, desde: date | None = None, hasta: date | None = None):
    d, h = _period(desde, hasta)
    return _download(exports.summary_csv(analytics.report(db, d, h)), f"resumen_{d}_{h}.csv", "text/csv; charset=utf-8")


@router.get("/reports/summary.pdf", tags=["reportes"])
def report_summary_pdf(db: DB, desde: date | None = None, hasta: date | None = None):
    d, h = _period(desde, hasta)
    return _download(exports.summary_pdf(analytics.report(db, d, h), utcnow()), f"resumen_{d}_{h}.pdf", "application/pdf")


@router.get("/reports/{name}.csv", tags=["reportes"])
def report_table(name: str, db: DB):
    builders = {"lotes": exports.lots_csv, "inspecciones": exports.inspections_csv, "decisiones": exports.decisions_csv}
    if name not in builders:
        raise HTTPException(404, "Reporte desconocido. Use lotes, inspecciones o decisiones.")
    return _download(builders[name](db), f"{name}.csv", "text/csv; charset=utf-8")


# ─── Modelo y demostración ──────────────────────────────────────────────────

@router.get("/model", tags=["modelo"])
def model_card(request: Request):
    rt = runtime_of(request)
    settings = settings_of(request)
    samples_file = settings.demo_data_dir / "images" / "samples.json"
    import json

    samples = json.loads(samples_file.read_text(encoding="utf-8")) if samples_file.exists() else {"imagenes": []}
    return {
        "loaded": rt.classifier is not None,
        "error": rt.model_error,
        "classifier": rt.classifier.metadata if rt.classifier else None,
        "metrics": rt.metrics,
        "rules": rules.RULES_CATALOG,
        "limitations": GENERAL_LIMITATIONS,
        "scenarios": list(rt.scenarios.values()),
        "samples": [{**s, "url": f"/samples/{s['archivo']}"} for s in samples["imagenes"]],
    }


@router.post("/demo/reset", tags=["demo"])
def reset_demo(request: Request, db: DB):
    settings = settings_of(request)
    if not settings.allow_reset:
        raise HTTPException(403, "El restablecimiento está deshabilitado (ALLOW_DEMO_RESET=false).")
    n = seed.reset_all(db, settings, runtime_of(request))
    return {"ok": True, "lotes_demo": n}
