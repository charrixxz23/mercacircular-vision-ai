"""Esquemas de entrada (validación con Pydantic). Las respuestas se documentan en docs/api.md."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LotCreate(BaseModel):
    product_id: int
    merchant_id: int
    area_id: int
    origin: str | None = Field(None, max_length=120, description="Procedencia (provincia/finca)")
    quantity: int | None = Field(None, ge=0, le=100000)
    quantity_unit: str = Field("cajas", max_length=20)
    weight_kg: float | None = Field(None, gt=0, le=100000)
    observations: str | None = Field(None, max_length=2000)
    registered_by: str | None = Field(None, max_length=120)


class LotUpdate(BaseModel):
    product_id: int | None = None
    merchant_id: int | None = None
    area_id: int | None = None
    origin: str | None = Field(None, max_length=120)
    quantity: int | None = Field(None, ge=0, le=100000)
    quantity_unit: str | None = Field(None, max_length=20)
    weight_kg: float | None = Field(None, gt=0, le=100000)
    observations: str | None = Field(None, max_length=2000)
    actor: str = Field(..., min_length=2, max_length=120, description="Quién realiza la edición")
    reason: str | None = Field(None, max_length=500, description="Motivo del cambio (queda en la trazabilidad)")


class InspectionCreate(BaseModel):
    mode: str = Field(..., pattern="^(ia|demo)$")
    image_id: int | None = None
    scenario_id: str | None = None
    actor: str | None = Field(None, max_length=120)


class DecisionCreate(BaseModel):
    action: str
    actor: str = Field(..., min_length=2, max_length=120)
    role: str = Field(..., min_length=2, max_length=80)
    notes: str | None = Field(None, max_length=2000)
    kg: float | None = Field(None, gt=0, le=100000)
    confirm: bool = False


class StatusChange(BaseModel):
    action: str = Field("marcar_pendiente")
    actor: str = Field(..., min_length=2, max_length=120)
