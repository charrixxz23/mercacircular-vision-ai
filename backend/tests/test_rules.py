"""Pruebas del motor de reglas y de la máquina de estados."""

from __future__ import annotations

from app.services.rules import recommend
from app.services.status import ACTIONS, available_actions


def base_result(**over):
    r = {
        "mode": "ia",
        "quality": {"summary": "buena", "checks": []},
        "identification": {"available": True, "declared": "tomate", "predicted": "tomate", "probability": 0.9,
                           "min_confidence": 0.6, "declared_in_model": True},
        "anomalies": {"count": 0, "affected_pct": 0.0},
    }
    r.update(over)
    return r


def codes(rec):
    return [x.rule for x in rec.reasons]


def test_insufficient_quality_requests_new_image():
    rec = recommend(base_result(quality={"summary": "insuficiente", "checks": [{"status": "error", "message": "Desenfocada"}]}), 100)
    assert rec.code == "nueva_imagen"
    assert rec.suggested_actions == ["solicitar_nueva_imagen"]
    assert "R01" in codes(rec)


def test_anomalies_require_human_review_with_priority():
    rec = recommend(base_result(anomalies={"count": 2, "affected_pct": 5.0}), 100)
    assert rec.code == "revision_humana" and rec.priority == "normal"
    rec = recommend(base_result(anomalies={"count": 4, "affected_pct": 25.0}), 100)
    assert rec.code == "revision_prioritaria" and rec.priority == "alta"
    assert rec.requires_human_confirmation is True
    assert "certifica" in rec.disclaimer


def test_no_anomalies_suggests_commercial_review():
    rec = recommend(base_result(), 100)
    assert rec.code == "revision_comercial"
    assert "R06" in codes(rec)


def test_product_mismatch_and_uncertainty():
    rec = recommend(base_result(identification={"available": True, "declared": "tomate", "predicted": "otro", "probability": 0.8,
                                                "min_confidence": 0.6, "declared_in_model": True}), 100)
    assert rec.code == "verificar_producto" and "R02" in codes(rec)
    rec = recommend(base_result(identification={"available": True, "declared": "tomate", "predicted": "otro", "probability": 0.4,
                                                "min_confidence": 0.6, "declared_in_model": True}), 100)
    assert rec.code == "revision_comercial" and "R03" in codes(rec)


def test_low_sensitivity_class_and_missing_weight_are_reported():
    rec = recommend(base_result(identification={"available": True, "declared": "papa", "predicted": "papa", "probability": 0.7,
                                                "min_confidence": 0.6, "declared_in_model": True}), None, {"papa": 0.24})
    assert {"R04", "R07"} <= set(codes(rec))


def test_banana_natural_spots_note_and_demo_mode_flag():
    r = base_result(mode="demo", identification={"available": False, "declared": "banano"}, anomalies={"count": 1, "affected_pct": 3})
    rec = recommend(r, 50)
    assert {"R05", "R08", "R09"} <= set(codes(rec))


def test_state_machine_actions():
    assert [a.code for a in available_actions("registrado")] == ["marcar_pendiente"]
    assert "confirmar_donacion" in [a.code for a in available_actions("evaluacion_donacion")]
    assert "confirmar_donacion" not in [a.code for a in available_actions("inspeccionado")]
    assert ACTIONS["confirmar_donacion"].requires_confirmation and ACTIONS["confirmar_donacion"].authorized_roles
    assert available_actions("cerrado") == []
