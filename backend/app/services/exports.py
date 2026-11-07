"""Exportación de reportes a CSV (UTF-8 con BOM, compatible con Excel) y PDF."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Decision, Inspection, Lot
from .analytics import INCIDENT_LABELS
from .status import DESTINATIONS, STATUSES

DISCLAIMER = ("Prototipo académico independiente desarrollado como caso de estudio para Merca Panamá. "
              "No representa un sistema oficial de la institución.")


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def to_csv(headers: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def lots_csv(db: Session) -> bytes:
    lots = db.scalars(select(Lot).order_by(Lot.created_at))
    return to_csv(
        ["lote", "datos_demostrativos", "producto", "comerciante", "area", "procedencia", "cantidad", "unidad", "peso_kg",
         "estado", "destino", "kg_recuperados", "kg_residuos", "registrado_utc", "primera_inspeccion_utc", "primera_decision_utc", "cierre_utc"],
        [[lot.code, "si" if lot.is_demo else "no", lot.product.name, lot.merchant.name, lot.area.name, lot.origin or "", lot.quantity or "",
          lot.quantity_unit, lot.weight_kg if lot.weight_kg is not None else "", STATUSES[lot.status], DESTINATIONS.get(lot.destination or "", ""),
          lot.recovered_kg or "", lot.waste_kg or "", _fmt(lot.created_at), _fmt(lot.inspected_at), _fmt(lot.decided_at), _fmt(lot.closed_at)]
         for lot in lots])


def inspections_csv(db: Session) -> bytes:
    rows = db.scalars(select(Inspection).options(selectinload(Inspection.lot)).order_by(Inspection.created_at))
    return to_csv(
        ["inspeccion", "lote", "datos_demostrativos", "modo", "escenario", "version_modelo", "producto_declarado", "producto_predicho",
         "probabilidad", "calidad", "regiones_marcadas", "pct_area_marcada", "incidencias", "recomendacion", "fecha_utc", "ms"],
        [[i.id, i.lot.code, "si" if i.is_demo else "no", i.mode, i.scenario or "", i.model_version or "", i.declared_product,
          i.predicted_product or "", i.prediction_score if i.prediction_score is not None else "", i.quality_summary or "",
          i.anomaly_count, i.affected_pct if i.affected_pct is not None else "",
          "; ".join(INCIDENT_LABELS.get(x, x) for x in (i.incidents or [])), (i.recommendation or {}).get("title", ""),
          _fmt(i.created_at), i.processing_ms or ""] for i in rows])


def decisions_csv(db: Session) -> bytes:
    rows = db.scalars(select(Decision).options(selectinload(Decision.lot)).order_by(Decision.created_at))
    return to_csv(
        ["decision", "lote", "datos_demostrativos", "accion", "responsable", "rol", "kg", "estado_anterior", "estado_nuevo",
         "recomendacion", "siguio_recomendacion", "notas", "fecha_utc"],
        [[d.id, d.lot.code, "si" if d.is_demo else "no", d.action, d.actor, d.role, d.kg if d.kg is not None else "",
          STATUSES[d.from_status], STATUSES[d.to_status], d.recommendation_code or "",
          "" if d.followed_recommendation is None else ("si" if d.followed_recommendation else "no"), d.notes or "", _fmt(d.created_at)]
         for d in rows])


def summary_csv(rep: dict) -> bytes:
    rows: list[list] = []
    for key, val in rep["comparacion"].items():
        rows.append(["comparacion", key, val["actual"], val["anterior"], "" if val["variacion_pct"] is None else val["variacion_pct"]])
    for prod, kg in rep["actual"]["kg_por_producto"].items():
        rows.append(["kg_por_producto", prod, kg, rep["anterior"]["kg_por_producto"].get(prod, 0), ""])
    for cat, n in rep["actual"]["incidencias"].items():
        rows.append(["incidencias", cat, n, rep["anterior"]["incidencias"].get(cat, 0), ""])
    for dest, kg in rep["actual"]["kg_destino_confirmado"].items():
        rows.append(["destino_kg_confirmado", dest, kg, rep["anterior"]["kg_destino_confirmado"].get(dest, 0), ""])
    for key, h in rep["actual"]["tiempos_horas"].items():
        rows.append(["tiempo_promedio_horas", key, "" if h is None else h, rep["anterior"]["tiempos_horas"].get(key) or "", ""])
    return to_csv(["seccion", "indicador", f"actual ({rep['periodo']['desde']} a {rep['periodo']['hasta']})",
                   f"anterior ({rep['periodo_anterior']['desde']} a {rep['periodo_anterior']['hasta']})", "variacion_pct"], rows)


class _PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 83, 45)
        self.cell(0, 8, "MercaCircular Vision AI - Reporte de excedentes", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(90, 90, 90)
        self.multi_cell(0, 4, DISCLAIMER, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Página {self.page_no()} · Datos demostrativos incluidos cuando así se indica", align="C")


def summary_pdf(rep: dict, generated: datetime) -> bytes:
    pdf = _PDF(format="A4")
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 10)
    p, pa = rep["periodo"], rep["periodo_anterior"]
    pdf.multi_cell(0, 5, f"Período: {p['desde']} a {p['hasta']} ({p['dias']} días). Comparado con: {pa['desde']} a {pa['hasta']}.\n"
                         f"Generado: {generated.strftime('%Y-%m-%d %H:%M')} UTC.", new_x="LMARGIN", new_y="NEXT")

    def table(title: str, headers: list[str], rows: list[list], widths: list[int]):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 240, 228)
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for r in rows:
            for v, w in zip(r, widths):
                pdf.cell(w, 6, str(v), border=1)
            pdf.ln()

    labels = {"lotes_registrados": "Lotes registrados", "kg_registrados": "Kg registrados (entrada)", "kg_observados": "Kg observados (con incidencias)",
              "kg_recuperado_donacion": "Kg donados (confirmados)", "kg_recuperado_comercial": "Kg comercializados (confirmados)",
              "kg_merma_confirmada": "Kg a residuos (confirmados)", "inspecciones": "Inspecciones"}
    table("Indicadores y comparación", ["Indicador", "Actual", "Anterior", "Variación"],
          [[labels[k], v["actual"], v["anterior"], "-" if v["variacion_pct"] is None else f"{v['variacion_pct']:+.1f} %"]
           for k, v in rep["comparacion"].items()], [80, 30, 30, 30])
    table("Kg registrados por producto", ["Producto", "Actual", "Anterior"],
          [[k, v, rep["anterior"]["kg_por_producto"].get(k, 0)] for k, v in rep["actual"]["kg_por_producto"].items()] or [["(sin datos)", "", ""]],
          [80, 30, 30])
    table("Incidencias por categoría", ["Categoría", "Actual", "Anterior"],
          [[k, v, rep["anterior"]["incidencias"].get(k, 0)] for k, v in rep["actual"]["incidencias"].items()], [80, 30, 30])
    table("Destino confirmado (kg)", ["Destino", "Actual", "Anterior"],
          [[k, v, rep["anterior"]["kg_destino_confirmado"].get(k, 0)] for k, v in rep["actual"]["kg_destino_confirmado"].items()], [80, 30, 30])
    t = rep["actual"]["tiempos_horas"]
    table("Tiempos promedio de procesamiento (horas)", ["Etapa", "Actual"],
          [["Registro a inspección", t["registro_a_inspeccion"] or "-"], ["Inspección a decisión", t["inspeccion_a_decision"] or "-"],
           ["Registro a cierre", t["registro_a_cierre"] or "-"]], [80, 30])
    pend = rep["lotes_pendientes"][:25]
    table(f"Lotes pendientes de inspección ({len(rep['lotes_pendientes'])})", ["Lote", "Producto", "Estado", "Kg", "Demo"],
          [[x["lote"], x["producto"], x["estado"], x["kg"] if x["kg"] is not None else "-", "sí" if x["demo"] else "no"] for x in pend] or [["(ninguno)", "", "", "", ""]],
          [32, 30, 52, 20, 16])
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, "Definiciones: " + " ".join(f"{k}: {v}" for k, v in rep["definiciones"].items()))
    return bytes(pdf.output())
