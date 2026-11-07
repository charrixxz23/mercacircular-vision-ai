"""Estados del lote, destinos y acciones de decisión humana (máquina de estados)."""

from __future__ import annotations

from dataclasses import dataclass

STATUSES: dict[str, str] = {
    "registrado": "Registrado",
    "pendiente_inspeccion": "Pendiente de inspección",
    "inspeccionado": "Inspeccionado",
    "revision_comercial": "Revisión comercial",
    "evaluacion_donacion": "Evaluación para donación",
    "gestion_residuos": "Gestión de residuos",
    "cerrado": "Cerrado",
}

DESTINATIONS: dict[str, str] = {
    "comercializado": "Comercializado tras revisión",
    "donacion": "Donación confirmada",
    "residuos": "Gestión de residuos",
}

# Roles que pueden confirmar la aptitud para donación (decisión exclusivamente humana).
AUTHORIZED_DONATION_ROLES = ["Inspector(a) de calidad", "Responsable de inocuidad"]
ROLES = AUTHORIZED_DONATION_ROLES + ["Supervisor(a) de nave", "Coordinador(a) comercial", "Operador(a) de recepción"]


@dataclass(frozen=True)
class Action:
    code: str
    label: str
    from_statuses: tuple[str, ...]
    to_status: str
    destination: str | None = None
    requires_kg: bool = False
    requires_confirmation: bool = False   # casilla de confirmación explícita
    authorized_roles: tuple[str, ...] = ()
    description: str = ""


ACTIONS: dict[str, Action] = {a.code: a for a in [
    Action("marcar_pendiente", "Enviar a inspección", ("registrado",), "pendiente_inspeccion",
           description="El lote queda en cola para ser fotografiado y analizado."),
    Action("solicitar_nueva_imagen", "Solicitar nueva imagen", ("inspeccionado",), "pendiente_inspeccion",
           description="La imagen no es suficiente; el lote vuelve a la cola de inspección."),
    Action("enviar_revision_comercial", "Enviar a revisión comercial", ("inspeccionado",), "revision_comercial",
           description="Un responsable comercial decide si el producto puede seguir a la venta."),
    Action("enviar_evaluacion_donacion", "Enviar a evaluación para donación", ("inspeccionado", "revision_comercial"), "evaluacion_donacion",
           description="Personal autorizado debe evaluar la aptitud para consumo antes de donar."),
    Action("enviar_gestion_residuos", "Enviar a gestión de residuos", ("inspeccionado", "revision_comercial", "evaluacion_donacion"), "gestion_residuos",
           description="El producto no puede aprovecharse y se destina a gestión de residuos."),
    Action("confirmar_comercializacion", "Confirmar comercialización", ("revision_comercial",), "cerrado", "comercializado", requires_kg=True,
           description="El responsable comercial confirma los kilogramos que siguen a la venta."),
    Action("confirmar_donacion", "Registrar donación", ("evaluacion_donacion",), "cerrado", "donacion",
           requires_kg=True, requires_confirmation=True, authorized_roles=tuple(AUTHORIZED_DONATION_ROLES),
           description="Solo personal autorizado. Confirma que evaluó la aptitud del producto; la IA no certifica inocuidad."),
    Action("confirmar_residuos", "Confirmar disposición como residuo", ("gestion_residuos",), "cerrado", "residuos", requires_kg=True,
           description="Registra los kilogramos entregados a gestión de residuos."),
]}


def available_actions(status: str) -> list[Action]:
    return [a for a in ACTIONS.values() if status in a.from_statuses]
