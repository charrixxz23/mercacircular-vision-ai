"""Modelo de datos (SQLAlchemy 2). Todas las fechas se guardan en UTC sin zona.

Tablas:
    products      catálogo de productos (tomate, banano, papa… ampliable)
    merchants     comerciantes ficticios
    areas         naves / áreas simuladas del mercado
    lots          lotes de excedentes
    lot_images    fotografías asociadas a un lote
    inspections   resultados de análisis (modo IA o demostrativo)
    decisions     decisiones humanas registradas (quién, qué, por qué)
    lot_events    línea de tiempo de trazabilidad (todo cambio queda registrado)
    app_meta      metadatos (fecha de carga de los datos demostrativos, etc.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)       # tomate, banano, papa
    name: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(9), default="#4d7c0f")  # para gráficos
    model_label: Mapped[str | None] = mapped_column(String(40))     # clase equivalente del modelo
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Area(Base):
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"))
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    origin: Mapped[str | None] = mapped_column(String(120))          # procedencia
    quantity: Mapped[int | None] = mapped_column(Integer)            # cajas / bultos
    quantity_unit: Mapped[str] = mapped_column(String(20), default="cajas")
    weight_kg: Mapped[float | None] = mapped_column(Float)
    observations: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True, default="registrado")
    destination: Mapped[str | None] = mapped_column(String(32))      # comercializado | donacion | residuos
    recovered_kg: Mapped[float | None] = mapped_column(Float)        # confirmado por una persona
    waste_kg: Mapped[float | None] = mapped_column(Float)            # confirmado por una persona
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    registered_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime)  # primera inspección
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)    # primera decisión humana
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    product: Mapped[Product] = relationship(lazy="joined")
    merchant: Mapped[Merchant] = relationship(lazy="joined")
    area: Mapped[Area] = relationship(lazy="joined")
    images: Mapped[list["LotImage"]] = relationship(back_populates="lot", cascade="all, delete-orphan", order_by="LotImage.id")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="lot", cascade="all, delete-orphan", order_by="Inspection.id")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="lot", cascade="all, delete-orphan", order_by="Decision.id")
    events: Mapped[list["LotEvent"]] = relationship(back_populates="lot", cascade="all, delete-orphan", order_by="LotEvent.id")


class LotImage(Base):
    __tablename__ = "lot_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))   # relativo a MEDIA_DIR
    original_name: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="upload")  # camera | upload | sample
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    lot: Mapped[Lot] = relationship(back_populates="images")


class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("lot_images.id", ondelete="SET NULL"))
    mode: Mapped[str] = mapped_column(String(10))       # ia | demo
    scenario: Mapped[str | None] = mapped_column(String(60))  # id del escenario (modo demo)
    model_version: Mapped[str | None] = mapped_column(String(40))
    declared_product: Mapped[str] = mapped_column(String(40))
    predicted_product: Mapped[str | None] = mapped_column(String(40))
    prediction_score: Mapped[float | None] = mapped_column(Float)
    quality_summary: Mapped[str | None] = mapped_column(String(20))  # buena | aceptable | insuficiente
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_pct: Mapped[float | None] = mapped_column(Float)
    incidents: Mapped[list] = mapped_column(JSON, default=list)       # categorías detectadas
    result: Mapped[dict] = mapped_column(JSON, default=dict)          # resultado completo
    recommendation: Mapped[dict] = mapped_column(JSON, default=dict)  # salida del motor de reglas
    annotated_filename: Mapped[str | None] = mapped_column(String(200))
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    performed_by: Mapped[str | None] = mapped_column(String(120))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    lot: Mapped[Lot] = relationship(back_populates="inspections")
    image: Mapped[LotImage | None] = relationship(lazy="joined")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    inspection_id: Mapped[int | None] = mapped_column(ForeignKey("inspections.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40))
    recommendation_code: Mapped[str | None] = mapped_column(String(40))
    followed_recommendation: Mapped[bool | None] = mapped_column(Boolean)
    actor: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    kg: Mapped[float | None] = mapped_column(Float)
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    lot: Mapped[Lot] = relationship(back_populates="decisions")


class LotEvent(Base):
    __tablename__ = "lot_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))   # creado | editado | imagen | inspeccion | estado | decision | peso
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(120))
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    lot: Mapped[Lot] = relationship(back_populates="events")


class AppMeta(Base):
    __tablename__ = "app_meta"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
