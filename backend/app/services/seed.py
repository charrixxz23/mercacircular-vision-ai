"""Carga del catálogo y de los datos demostrativos (``demo-data/seed.json``).

Los lotes demostrativos se reproducen con las MISMAS funciones de negocio que
usa la aplicación (estados, decisiones, eventos), con fechas relativas al día
de carga. Quedan marcados con ``is_demo = True`` en todas las tablas.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AppMeta, Area, Decision, Inspection, Lot, LotEvent, LotImage, Merchant, Product, utcnow
from . import inspections as insp_service
from . import lots as lot_service

# Las horas de seed.json son horas locales de Panamá (UTC−5); en la base se guarda UTC.
PANAMA_UTC_OFFSET_H = 5


def load_seed(settings: Settings) -> dict:
    return json.loads((settings.demo_data_dir / "seed.json").read_text(encoding="utf-8"))


def ensure_catalog(db: Session, seed: dict) -> None:
    for p in seed["products"]:
        if db.scalar(select(Product).where(Product.code == p["code"])) is None:
            db.add(Product(code=p["code"], name=p["name"], color=p["color"], model_label=p.get("model_label")))
    for name in seed["merchants"]:
        if db.scalar(select(Merchant).where(Merchant.name == name)) is None:
            db.add(Merchant(name=name, is_demo=True))
    for name in seed["areas"]:
        if db.scalar(select(Area).where(Area.name == name)) is None:
            db.add(Area(name=name))
    db.flush()


def seed_demo(db: Session, settings: Settings, runtime: insp_service.VisionRuntime, base: datetime | None = None) -> int:
    seed = load_seed(settings)
    ensure_catalog(db, seed)
    if db.scalar(select(Lot.id).where(Lot.is_demo.is_(True)).limit(1)) is not None:
        return 0
    now = base or utcnow()
    # Medianoche de HOY en Panamá, expresada en UTC.
    local = now - timedelta(hours=PANAMA_UTC_OFFSET_H)
    base = local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=PANAMA_UTC_OFFSET_H)
    products = {p.code: p for p in db.scalars(select(Product))}
    merchants = {m.name: m for m in db.scalars(select(Merchant))}
    areas = {a.name: a for a in db.scalars(select(Area))}
    people = seed["people"]
    reception = people["recepcion"]["name"]

    created = 0
    for item in seed["lots"]:
        day = base - timedelta(days=item["day_offset"])
        if day + timedelta(hours=item["hour"]) > now:
            continue  # todavía no "ocurre" a esta hora del día
        created += 1
        lot = lot_service.create_lot(db, {
            "product_id": products[item["product"]].id, "merchant_id": merchants[seed["merchants"][item["merchant"]]].id,
            "area_id": areas[seed["areas"][item["area"]]].id, "origin": item["origin"], "quantity": item["quantity"],
            "quantity_unit": item["unit"], "weight_kg": item["weight_kg"], "observations": item["observations"],
        }, actor=reception, at=day + timedelta(hours=item["hour"]), is_demo=True, code=item["code"])
        for step in item["steps"]:
            at = day + timedelta(hours=step["h"])
            if at > now:
                break  # el resto del historial queda pendiente: nunca se crean eventos en el futuro
            if step["type"] == "peso":
                lot_service.update_lot(db, lot, {"weight_kg": step["kg"]}, actor=reception, at=at)
            elif step["type"] == "marcar_pendiente":
                lot_service.transition(db, lot, "pendiente_inspeccion", actor=reception, at=at)
            elif step["type"] == "inspeccion":
                insp_service.run_inspection(db, lot, mode="demo", scenario_id=step["scenario"], settings=settings, runtime=runtime,
                                            actor=people["inspector"]["name"], at=at, is_demo=True)
            elif step["type"] == "decision":
                who = people[step["who"]]
                lot_service.apply_decision(db, lot, step["action"], actor=who["name"], role=who["role"], notes=step.get("notes"),
                                           kg=step.get("kg"), confirm=step["action"] == "confirmar_donacion", at=at, is_demo=True)
    meta = db.get(AppMeta, "demo_seed_date") or AppMeta(key="demo_seed_date", value="")
    meta.value = base.date().isoformat()
    db.merge(meta)
    db.commit()
    return created


def reset_all(db: Session, settings: Settings, runtime: insp_service.VisionRuntime) -> int:
    """Borra TODOS los lotes (demo y propios) y vuelve a cargar la demostración."""
    for model in (LotEvent, Decision, Inspection, LotImage, Lot):
        db.execute(delete(model))
    db.commit()
    media = settings.media_dir / "lots"
    if media.exists():
        import shutil

        shutil.rmtree(media)
    return seed_demo(db, settings, runtime)
