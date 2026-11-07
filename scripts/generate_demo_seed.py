"""Genera demo-data/seed.json: historial SINTÉTICO de lotes para la demostración.

    python scripts/generate_demo_seed.py

Es determinista (semilla fija): siempre produce el mismo archivo. Las fechas se
guardan como desfases (días y hora) respecto al día en que se carga la base de
datos, para que el historial siempre termine "hoy". Una vez cargados, los datos
quedan en la base y no cambian al refrescar la página.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo-data" / "seed.json"
SEED = 507
DAYS = 84  # 12 semanas

PRODUCTS = [
    {"code": "tomate", "name": "Tomate", "color": "#dc2626", "model_label": "tomate"},
    {"code": "banano", "name": "Banano", "color": "#ca8a04", "model_label": "banano"},
    {"code": "papa", "name": "Papa", "color": "#92400e", "model_label": "papa"},
]
MERCHANTS = ["Agro Demo Los Valles", "Distribuidora Demo Altamira", "Comercial Demo El Higo", "Frutas Demo del Atlántico",
             "Hortalizas Demo Tierras Altas", "Mayorista Demo La Llanura"]
AREAS = ["Nave 1 · Frutas", "Nave 2 · Hortalizas", "Nave 3 · Tubérculos y raíces", "Andén de recepción", "Cámara de frío"]
ORIGINS = {
    "tomate": ["Chiriquí (Boquete)", "Coclé (Penonomé)", "Los Santos", "Herrera (Chitré)"],
    "banano": ["Bocas del Toro", "Chiriquí (Barú)", "Panamá Oeste"],
    "papa": ["Chiriquí (Cerro Punta)", "Chiriquí (Volcán)"],
}
AREA_BY_PRODUCT = {"tomate": [1, 3, 4], "banano": [0, 3], "papa": [2, 3]}
PEOPLE = {
    "recepcion": ("R. Gómez (ficticio)", "Operador(a) de recepción"),
    "inspector": ("A. Ríos (ficticia)", "Inspector(a) de calidad"),
    "inocuidad": ("L. Méndez (ficticia)", "Responsable de inocuidad"),
    "comercial": ("C. Pérez (ficticio)", "Coordinador(a) comercial"),
    "supervisor": ("J. Castillo (ficticio)", "Supervisor(a) de nave"),
}
WEIGHTS = {"tomate": (80, 600), "banano": (150, 900), "papa": (200, 1200)}
# Probabilidad de escenarios por producto: sin_anomalias, manchas_leves, deterioro_extenso, imagen_insuficiente
SCENARIO_P = {"tomate": [0.50, 0.28, 0.14, 0.08], "banano": [0.40, 0.38, 0.14, 0.08], "papa": [0.58, 0.24, 0.10, 0.08]}
SCENARIOS = ["sin_anomalias", "manchas_leves", "deterioro_extenso", "imagen_insuficiente"]


def main() -> None:
    rng = random.Random(SEED)
    lots = []
    n = 0
    for day in range(DAYS, -1, -1):
        for _ in range(rng.choice([0, 1, 1, 1, 2])):
            n += 1
            prod = rng.choices(["tomate", "banano", "papa"], [0.45, 0.33, 0.22])[0]
            lo, hi = WEIGHTS[prod]
            weight = round(rng.uniform(lo, hi) / 5) * 5
            hour = rng.randint(5, 14)
            lot = {
                "code": f"MC-D-{n:04d}", "product": prod, "merchant": rng.randrange(len(MERCHANTS)),
                "area": rng.choice(AREA_BY_PRODUCT[prod]), "origin": rng.choice(ORIGINS[prod]),
                "quantity": max(1, round(weight / rng.choice([18, 20, 22, 25]))), "unit": "cajas" if prod != "papa" else "sacos",
                "weight_kg": weight if rng.random() > 0.05 or day < 2 else None,
                "observations": rng.choice([None, None, "Excedente del día anterior.", "Sin comprador al cierre.", "Cajas con golpes en el transporte."]),
                "day_offset": day, "hour": hour, "steps": [],
            }
            t = hour + rng.uniform(0.5, 3)
            if day <= 2 and rng.random() < 0.7:
                if rng.random() < 0.5:
                    lot["steps"].append({"type": "marcar_pendiente", "h": round(t, 2)})
                lots.append(lot)
                continue
            if lot["weight_kg"] is None:
                lot["steps"].append({"type": "peso", "h": round(t - 0.3, 2), "kg": round(rng.uniform(lo, hi) / 5) * 5})
                weight = lot["steps"][-1]["kg"]
            sc = rng.choices(SCENARIOS, SCENARIO_P[prod])[0]
            lot["steps"].append({"type": "inspeccion", "h": round(t, 2), "scenario": sc})
            t += rng.uniform(0.3, 2.0)
            if sc == "imagen_insuficiente":
                lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "solicitar_nueva_imagen", "who": "inspector"})
                t += rng.uniform(0.3, 1.5)
                sc = rng.choices(SCENARIOS[:3], SCENARIO_P[prod][:3])[0]
                lot["steps"].append({"type": "inspeccion", "h": round(t, 2), "scenario": sc})
                t += rng.uniform(0.3, 2.0)
            recent = day <= 3 and rng.random() < 0.5
            if sc == "sin_anomalias":
                lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "enviar_revision_comercial", "who": "supervisor"})
                if not recent:
                    t += rng.uniform(2, 20)
                    if rng.random() < 0.8:
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "confirmar_comercializacion", "who": "comercial",
                                             "kg": round(weight * rng.uniform(0.85, 1.0))})
                    else:
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "enviar_evaluacion_donacion", "who": "comercial"})
                        t += rng.uniform(2, 10)
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "confirmar_donacion", "who": "inocuidad",
                                             "kg": round(weight * rng.uniform(0.7, 0.95))})
            elif sc == "manchas_leves":
                lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "enviar_evaluacion_donacion", "who": "inspector"})
                if not recent:
                    t += rng.uniform(2, 24)
                    if rng.random() < 0.75:
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "confirmar_donacion",
                                             "who": rng.choice(["inspector", "inocuidad"]), "kg": round(weight * rng.uniform(0.55, 0.9))})
                    else:
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "enviar_gestion_residuos", "who": "inocuidad",
                                             "notes": "No apto tras evaluación presencial."})
                        t += rng.uniform(2, 12)
                        lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "confirmar_residuos", "who": "supervisor",
                                             "kg": round(weight * rng.uniform(0.9, 1.0))})
            else:  # deterioro_extenso
                lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "enviar_gestion_residuos", "who": "inspector"})
                if not recent:
                    t += rng.uniform(2, 12)
                    lot["steps"].append({"type": "decision", "h": round(t, 2), "action": "confirmar_residuos", "who": "supervisor",
                                         "kg": round(weight * rng.uniform(0.9, 1.0))})
            lots.append(lot)

    data = {
        "_aviso": "DATOS SINTÉTICOS DEMOSTRATIVOS generados por scripts/generate_demo_seed.py (semilla fija). "
                  "Comerciantes, personas y lotes son ficticios. No representan operaciones reales de Merca Panamá.",
        "products": PRODUCTS, "merchants": MERCHANTS, "areas": AREAS,
        "people": {k: {"name": v[0], "role": v[1]} for k, v in PEOPLE.items()},
        "lots": lots,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(lots)} lotes → {OUT}")


if __name__ == "__main__":
    main()
