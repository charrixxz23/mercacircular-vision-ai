"""Motor de reglas: convierte el resultado del análisis en una RECOMENDACIÓN.

Principios:
- Cada regla es explícita, tiene un identificador y produce una razón legible.
- La recomendación siempre requiere confirmación humana.
- Ninguna regla certifica inocuidad ni aptitud para consumo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

AFFECTED_PRIORITY_PCT = 15.0   # % del producto con manchas para marcar revisión prioritaria
LOW_SENSITIVITY = 0.6          # sensibilidad de prueba por debajo de la cual se advierte

RULES_CATALOG = [
    {"id": "R01", "nombre": "Imagen insuficiente", "condicion": "Alguna verificación de calidad en 'error' (resolución, exposición, nitidez o producto no visible).",
     "efecto": "Recomendar nueva imagen; no se sugiere destino."},
    {"id": "R02", "nombre": "Producto no coincide", "condicion": "El modelo identifica otra clase con probabilidad ≥ umbral del modelo.",
     "efecto": "Revisión humana para verificar el producto declarado."},
    {"id": "R03", "nombre": "Identificación incierta", "condicion": "La probabilidad máxima del modelo es menor que su umbral.",
     "efecto": "Se informa; prevalece el producto declarado por el operador."},
    {"id": "R04", "nombre": "Clase poco fiable", "condicion": "La sensibilidad de prueba para el producto declarado es < 60 %.",
     "efecto": "Se advierte que la identificación automática no es fiable para ese producto."},
    {"id": "R05", "nombre": "Indicios de deterioro", "condicion": "El detector marca al menos una región oscura.",
     "efecto": "Revisión humana; si el área afectada es ≥ 15 %, revisión prioritaria."},
    {"id": "R06", "nombre": "Sin indicios visibles", "condicion": "Calidad suficiente y ninguna región marcada.",
     "efecto": "Sugerir revisión comercial (el producto podría seguir a la venta)."},
    {"id": "R07", "nombre": "Peso pendiente", "condicion": "El lote no tiene peso registrado.",
     "efecto": "Registrar el peso antes de cerrar el lote."},
    {"id": "R08", "nombre": "Manchas naturales", "condicion": "Producto banano con regiones marcadas.",
     "efecto": "Advertir que la maduración normal también produce manchas oscuras."},
    {"id": "R09", "nombre": "Escenario demostrativo", "condicion": "El análisis es del modo demostrativo.",
     "efecto": "Se indica que el resultado es predefinido y no proviene de un modelo."},
]


@dataclass
class Reason:
    rule: str
    text: str
    level: str = "info"  # info | advertencia | critico


@dataclass
class Recommendation:
    code: str
    title: str
    summary: str
    priority: str                              # normal | alta
    suggested_actions: list[str] = field(default_factory=list)
    reasons: list[Reason] = field(default_factory=list)
    requires_human_confirmation: bool = True
    disclaimer: str = ("Recomendación automática sujeta a revisión. La decisión final sobre aptitud para consumo "
                       "o donación corresponde a personal autorizado; el sistema no certifica inocuidad.")

    def to_dict(self) -> dict:
        return asdict(self)


def recommend(result: dict, lot_weight_kg: float | None, class_sensitivity: dict[str, float] | None = None) -> Recommendation:
    """``result`` es la salida de ``vision.pipeline.analyze`` o de un escenario demostrativo."""
    reasons: list[Reason] = []
    declared = result.get("identification", {}).get("declared")

    if result.get("mode") == "demo":
        reasons.append(Reason("R09", "Resultado predefinido de un escenario demostrativo; no lo generó un modelo de visión.", "advertencia"))

    # R01 — calidad
    quality = result.get("quality", {})
    errors = [c for c in quality.get("checks", []) if c.get("status") == "error"]
    if quality.get("summary") == "insuficiente":
        for c in errors or [{"message": "La calidad de la imagen es insuficiente."}]:
            reasons.append(Reason("R01", c["message"], "critico"))
        if lot_weight_kg is None:
            reasons.append(Reason("R07", "Registre también el peso del lote.", "advertencia"))
        return Recommendation(
            code="nueva_imagen", title="Solicitar una nueva imagen",
            summary="La imagen no permite un análisis fiable. Tome otra foto con el producto centrado, enfocado y bien iluminado.",
            priority="normal", suggested_actions=["solicitar_nueva_imagen"], reasons=reasons)

    # R02–R04 — identificación
    ident = result.get("identification", {})
    mismatch = False
    if ident.get("available"):
        pred, prob, thr = ident.get("predicted"), ident.get("probability") or 0.0, ident.get("min_confidence", 0.6)
        if ident.get("declared_in_model") is False:
            reasons.append(Reason("R03", f"«{declared}» no está entre las clases del modelo; la identificación es solo orientativa.", "info"))
        elif pred != declared and prob >= thr:
            mismatch = True
            reasons.append(Reason("R02", f"El modelo identifica «{pred}» ({prob:.0%}) pero se declaró «{declared}».", "advertencia"))
        elif prob < thr:
            reasons.append(Reason("R03", f"Identificación incierta (probabilidad {prob:.0%} < umbral {thr:.0%}); se usa el producto declarado.", "info"))
        else:
            reasons.append(Reason("R03", f"El modelo coincide con el producto declarado ({prob:.0%}).", "info"))
    sens = (class_sensitivity or {}).get(declared)
    if sens is not None and sens < LOW_SENSITIVITY:
        reasons.append(Reason("R04", f"En la validación, el modelo reconoció correctamente solo el {sens:.0%} de las imágenes de {declared}: "
                                     "la identificación automática no es fiable para este producto.", "advertencia"))

    # R05–R08 — anomalías
    anom = result.get("anomalies", {})
    count = int(anom.get("count") or 0)
    affected = float(anom.get("affected_pct") or 0.0)
    if lot_weight_kg is None:
        reasons.append(Reason("R07", "El lote no tiene peso registrado; regístrelo antes de cerrar.", "advertencia"))

    if count > 0:
        level = "critico" if affected >= AFFECTED_PRIORITY_PCT else "advertencia"
        reasons.insert(0, Reason("R05", f"Se marcaron {count} región(es) más oscuras que su entorno ({affected:.1f} % del producto visible).", level))
        if declared == "banano":
            reasons.append(Reason("R08", "En banano, la maduración normal produce manchas oscuras: verifique si es deterioro.", "info"))
        priority = "alta" if affected >= AFFECTED_PRIORITY_PCT else "normal"
        return Recommendation(
            code="revision_prioritaria" if priority == "alta" else "revision_humana",
            title="Revisión humana prioritaria" if priority == "alta" else "Revisión humana de anomalías",
            summary=("Hay indicios visuales de deterioro. Un responsable debe inspeccionar el lote y decidir si sigue a revisión comercial, "
                     "a evaluación para donación o a gestión de residuos."),
            priority=priority,
            suggested_actions=["enviar_revision_comercial", "enviar_evaluacion_donacion", "enviar_gestion_residuos"],
            reasons=reasons)

    if mismatch:
        return Recommendation(
            code="verificar_producto", title="Verificar el producto declarado",
            summary="La identificación automática no coincide con lo declarado. Confirme el producto o tome otra foto.",
            priority="normal", suggested_actions=["solicitar_nueva_imagen", "enviar_revision_comercial"], reasons=reasons)

    reasons.insert(0, Reason("R06", "No se marcaron regiones oscuras en la parte visible del producto.", "info"))
    return Recommendation(
        code="revision_comercial", title="Continuar a revisión comercial",
        summary=("No se observaron indicios visibles de deterioro en esta imagen. Un responsable comercial puede confirmar si el lote "
                 "sigue a la venta. La foto solo muestra una cara del producto."),
        priority="normal",
        suggested_actions=["enviar_revision_comercial", "enviar_evaluacion_donacion", "enviar_gestion_residuos"],
        reasons=reasons)
