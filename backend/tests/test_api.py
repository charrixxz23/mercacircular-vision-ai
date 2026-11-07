"""Pruebas de integración de la API (flujo completo, persistencia, reportes)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import SAMPLES, jpeg, make_settings, synthetic_fruit

INSPECTOR = {"actor": "Prueba Inspectora", "role": "Inspector(a) de calidad"}


def catalog_ids(client):
    cat = client.get("/api/catalog").json()
    prod = {p["code"]: p["id"] for p in cat["products"]}
    return prod, cat["merchants"][0]["id"], cat["areas"][0]["id"]


def new_lot(client, product="tomate", weight=120.0):
    prod, merchant, area = catalog_ids(client)
    r = client.post("/api/lots", json={"product_id": prod[product], "merchant_id": merchant, "area_id": area,
                                       "origin": "Chiriquí", "quantity": 6, "weight_kg": weight, "registered_by": "Prueba"})
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, code, data: bytes, name="foto.jpg", source="upload"):
    r = client.post(f"/api/lots/{code}/images", files={"file": (name, data, "image/jpeg")}, data={"source": source, "actor": "Prueba"})
    assert r.status_code == 201, r.text
    return r.json()


def test_health_and_seed(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["model_loaded"] is True
    lots = client.get("/api/lots", params={"demo": True, "limit": 500}).json()
    assert lots["total"] > 50
    assert all(item["is_demo"] for item in lots["items"])


def test_seed_is_stable_between_requests(client):
    a = client.get("/api/dashboard").json()["kpis"]
    b = client.get("/api/dashboard").json()["kpis"]
    assert a == b


def test_full_flow_ia_mode(client):
    lot = new_lot(client)
    code = lot["code"]
    assert lot["status"] == "registrado" and lot["is_demo"] is False

    img = upload(client, code, (SAMPLES / "tomate_manchas_sinteticas.jpg").read_bytes(), source="sample")
    assert client.get(f"/api/lots/{code}").json()["status"] == "pendiente_inspeccion"

    r = client.post(f"/api/lots/{code}/inspections", json={"mode": "ia", "image_id": img["id"], "actor": "Prueba"})
    assert r.status_code == 201, r.text
    insp = r.json()
    assert insp["mode"] == "ia" and insp["result"]["identification"]["predicted"] == "tomate"
    assert insp["anomaly_count"] >= 1 and insp["annotated_url"]
    assert insp["recommendation"]["code"] in {"revision_humana", "revision_prioritaria"}
    assert "manchas_oscuras" in insp["incidents"]
    assert client.get(insp["annotated_url"]).status_code == 200

    detail = client.get(f"/api/lots/{code}").json()
    assert detail["status"] == "inspeccionado"
    suggested = {a["code"] for a in detail["available_actions"] if a["suggested"]}
    assert "enviar_evaluacion_donacion" in suggested

    r = client.post(f"/api/lots/{code}/decisions", json={"action": "enviar_evaluacion_donacion", **INSPECTOR})
    assert r.status_code == 201 and r.json()["status"] == "evaluacion_donacion"

    # Donar sin confirmación o con un rol no autorizado debe fallar.
    bad = client.post(f"/api/lots/{code}/decisions", json={"action": "confirmar_donacion", "kg": 90, **INSPECTOR})
    assert bad.status_code == 400
    bad = client.post(f"/api/lots/{code}/decisions", json={"action": "confirmar_donacion", "kg": 90, "confirm": True,
                                                           "actor": "Carlos Prueba", "role": "Coordinador(a) comercial"})
    assert bad.status_code == 403
    bad = client.post(f"/api/lots/{code}/decisions", json={"action": "confirmar_donacion", "kg": 500, "confirm": True, **INSPECTOR})
    assert bad.status_code == 400  # más kg que el lote

    r = client.post(f"/api/lots/{code}/decisions", json={"action": "confirmar_donacion", "kg": 90, "confirm": True,
                                                         "notes": "Apto tras revisión presencial", **INSPECTOR})
    assert r.status_code == 201
    final = r.json()
    assert final["status"] == "cerrado" and final["destination"] == "donacion" and final["recovered_kg"] == 90
    assert final["decision_list"][0]["actor"] == "Prueba Inspectora"
    types = [e["type"] for e in final["timeline"]]
    assert types[0] == "creado" and {"imagen", "inspeccion", "decision", "estado"} <= set(types)

    # Lote cerrado: no se edita.
    r = client.patch(f"/api/lots/{code}", json={"weight_kg": 10, "actor": "Prueba"})
    assert r.status_code == 409


def test_dashboard_reflects_new_lot(empty_client):
    c = empty_client
    before = c.get("/api/dashboard").json()["kpis"]
    assert before["lotes_registrados"] == 0
    lot = new_lot(c, weight=200)
    k = c.get("/api/dashboard").json()["kpis"]
    assert k["lotes_registrados"] == 1 and k["kg_registrados"] == 200 and k["pendientes_inspeccion"] == 1
    c.post(f"/api/lots/{lot['code']}/inspections", json={"mode": "demo", "scenario_id": "deterioro_extenso"})
    c.post(f"/api/lots/{lot['code']}/decisions", json={"action": "enviar_gestion_residuos", **INSPECTOR})
    c.post(f"/api/lots/{lot['code']}/decisions", json={"action": "confirmar_residuos", "kg": 180, **INSPECTOR})
    k = c.get("/api/dashboard").json()["kpis"]
    assert k["kg_residuos_confirmados"] == 180 and k["kg_donacion_confirmada"] == 0 and k["pendientes_inspeccion"] == 0


def test_demo_mode_is_labeled_and_has_no_regions(empty_client):
    lot = new_lot(empty_client)
    img = upload(empty_client, lot["code"], jpeg(synthetic_fruit()))
    r = empty_client.post(f"/api/lots/{lot['code']}/inspections", json={"mode": "demo", "scenario_id": "manchas_leves", "image_id": img["id"]})
    insp = r.json()
    assert insp["mode"] == "demo" and insp["result"]["anomalies"]["regions"] == []
    assert insp["prediction_score"] is None and insp["annotated_url"] is None
    assert any("DEMOSTRATIVO" in x for x in insp["result"]["limitations"])
    assert any(x["rule"] == "R09" for x in insp["recommendation"]["reasons"])


def test_validation_errors(empty_client):
    c = empty_client
    lot = new_lot(c)
    assert c.post(f"/api/lots/{lot['code']}/images", files={"file": ("x.jpg", b"no", "image/jpeg")}).status_code == 415
    assert c.post(f"/api/lots/{lot['code']}/inspections", json={"mode": "ia"}).status_code == 400
    assert c.post(f"/api/lots/{lot['code']}/inspections", json={"mode": "demo", "scenario_id": "nope"}).status_code == 400
    assert c.post(f"/api/lots/{lot['code']}/decisions", json={"action": "confirmar_residuos", "kg": 1, **INSPECTOR}).status_code == 409
    assert c.get("/api/lots/NO-EXISTE").status_code == 404
    prod, merchant, area = catalog_ids(c)
    assert c.post("/api/lots", json={"product_id": 999, "merchant_id": merchant, "area_id": area}).status_code == 400
    assert c.post("/api/lots", json={"product_id": prod["papa"], "merchant_id": merchant, "area_id": area, "weight_kg": -5}).status_code == 422


def test_controlled_edit_and_weight_event(empty_client):
    c = empty_client
    prod, merchant, area = catalog_ids(c)
    r = c.post("/api/lots", json={"product_id": prod["papa"], "merchant_id": merchant, "area_id": area})
    code = r.json()["code"]
    r = c.patch(f"/api/lots/{code}", json={"weight_kg": 350, "actor": "Supervisora", "reason": "Pesaje en báscula"})
    assert r.status_code == 200
    ev = r.json()["timeline"][-1]
    assert ev["type"] == "peso" and ev["actor"] == "Supervisora" and ev["payload"]["cambios"]["weight_kg"]["despues"] == 350
    c.post(f"/api/lots/{code}/inspections", json={"mode": "demo", "scenario_id": "sin_anomalias"})
    assert c.patch(f"/api/lots/{code}", json={"product_id": prod["tomate"], "actor": "Carlos Prueba"}).status_code == 409


def test_search_and_filters(client):
    all_ = client.get("/api/lots", params={"limit": 500}).json()["total"]
    tomate = client.get("/api/lots", params={"product": "tomate", "limit": 500}).json()
    assert 0 < tomate["total"] < all_ and all(i["product"]["code"] == "tomate" for i in tomate["items"])
    closed = client.get("/api/lots", params={"status": "cerrado", "limit": 500}).json()
    assert all(i["status"] == "cerrado" for i in closed["items"])
    found = client.get("/api/lots", params={"q": "MC-D-0001"}).json()
    assert found["total"] == 1


def test_reports_csv_and_pdf(client):
    rep = client.get("/api/reports/summary").json()
    assert set(rep["comparacion"]) >= {"kg_registrados", "kg_recuperado_donacion", "kg_merma_confirmada"}
    assert "definiciones" in rep
    csv = client.get("/api/reports/lotes.csv")
    assert csv.status_code == 200 and csv.content.startswith("﻿".encode()) and b"MC-D-0001" in csv.content
    for name in ("inspecciones", "decisiones"):
        assert client.get(f"/api/reports/{name}.csv").status_code == 200
    assert client.get("/api/reports/summary.csv").status_code == 200
    pdf = client.get("/api/reports/summary.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert client.get("/api/reports/summary", params={"desde": "2026-02-01", "hasta": "2026-01-01"}).status_code == 400


def test_model_card(client):
    card = client.get("/api/model").json()
    assert card["loaded"] and card["metrics"]["clasificador"]["prueba"]["matriz_confusion"]
    assert len(card["rules"]) >= 8 and card["samples"]


def test_data_persists_after_restart(tmp_path):
    settings = make_settings(tmp_path, seed=False)
    with TestClient(create_app(settings)) as c:
        code = new_lot(c)["code"]
        upload(c, code, jpeg(synthetic_fruit()))
    with TestClient(create_app(make_settings(tmp_path, seed=False))) as c2:
        lot = c2.get(f"/api/lots/{code}").json()
        assert lot["code"] == code and len(lot["image_list"]) == 1
        assert c2.get(lot["image_list"][0]["url"]).status_code == 200


def test_reset_restores_demo(client):
    new_lot(client)
    assert client.get("/api/dashboard").json()["kpis"]["lotes_reales"] == 1
    assert client.post("/api/demo/reset").status_code == 200
    k = client.get("/api/dashboard").json()["kpis"]
    assert k["lotes_reales"] == 0 and k["lotes_demo"] > 0
