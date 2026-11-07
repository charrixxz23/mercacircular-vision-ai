"""Validación SINTÉTICA del detector de manchas oscuras.

    python -m ml.evaluate_anomalies

No existe (en este proyecto) un conjunto de datos de tomate/banano/papa con
defectos reales etiquetados. Para medir al menos el comportamiento del
algoritmo se hace lo siguiente:

1. Se toman imágenes LIMPIAS de tomate, banano y papa (puestas sobre fondos aleatorios).
2. A una copia se le pintan 1–3 manchas irregulares con un oscurecimiento conocido
   (20–70 en la escala L de OpenCV; "leve" < 40 ≤ "marcada").
3. Se mide, por producto:
   - sensibilidad: % de imágenes con manchas donde el detector marca alguna región que toca una mancha;
   - falsos positivos: % de imágenes limpias en las que el detector marca algo;
   - precisión de regiones: % de regiones marcadas que tocan una mancha real.
4. Los parámetros se eligen con los grupos de ENTRENAMIENTO y se reportan en los de PRUEBA.

Esto mide el algoritmo, NO su desempeño con defectos reales del mercado.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.vision.anomalies import DEFAULT_PARAMS, detect  # noqa: E402
from app.vision.segmentation import segment  # noqa: E402
from ml.augment import add_blemishes, composite  # noqa: E402
from ml.dataset import build  # noqa: E402

PRODUCTS = ["tomate", "banano", "papa"]
PER_PRODUCT = {"train": 120, "test": 150}
GRID = {"delta_l": [18.0, 22.0, 28.0, 34.0], "min_area_frac": [0.008, 0.015], "local_k_frac": [0.25, 0.5], "local_factor": [0.0, 0.6]}


def prepare(split: str):
    rng = np.random.default_rng(7 if split == "train" else 11)
    items = []
    for prod in PRODUCTS:
        pool = [s for s in build() if s.label == prod and s.split == split]
        for i in rng.choice(len(pool), size=min(PER_PRODUCT[split], len(pool)), replace=False):
            s = pool[i]
            photo = composite(cv2.imread(str(s.path)), np.random.default_rng(s.seed))
            seg = segment(photo)
            if seg.bbox is None:
                continue
            dirty, truth, drop = add_blemishes(photo, seg.main_mask, np.random.default_rng(s.seed + 1))
            seg_dirty = segment(dirty)
            if seg_dirty.bbox is None or not truth.any():
                continue
            items.append((prod, photo, seg.main_mask, dirty, seg_dirty.main_mask, truth, drop))
    return items


def evaluate(items, params) -> dict:
    out = {}
    for prod in PRODUCTS:
        sel = [it for it in items if it[0] == prod]
        tp_img = fp_img = 0
        reg_total = reg_hit = 0
        by_severity = {"leve": [0, 0], "marcada": [0, 0]}  # [detectadas, total]
        for _, clean, m_clean, dirty, m_dirty, truth, drop in sel:
            regions, _, _ = detect(clean, m_clean, params)
            fp_img += bool(regions)
            regions, _, _ = detect(dirty, m_dirty, params)
            hits = [r for r in regions if truth[r.y:r.y + r.h, r.x:r.x + r.w].any()]
            tp_img += bool(hits)
            bucket = by_severity["leve" if drop < 40 else "marcada"]
            bucket[0] += bool(hits)
            bucket[1] += 1
            reg_total += len(regions)
            reg_hit += len(hits)
        n = max(len(sel), 1)
        out[prod] = {
            "imagenes": len(sel),
            "sensibilidad": round(tp_img / n, 4),
            "falsos_positivos_imagenes_limpias": round(fp_img / n, 4),
            "precision_regiones": round(reg_hit / reg_total, 4) if reg_total else None,
            "sensibilidad_por_severidad": {k: {"detectadas": v[0], "total": v[1], "tasa": round(v[0] / v[1], 4) if v[1] else None}
                                           for k, v in by_severity.items()},
        }
    return out


def main() -> int:
    train = prepare("train")
    best, best_score = None, -1.0
    tuning = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        params = {**DEFAULT_PARAMS, **dict(zip(keys, combo))}
        res = evaluate(train, params)
        # Índice de Youden promedio por producto (sensibilidad − falsos positivos).
        score = float(np.mean([r["sensibilidad"] - r["falsos_positivos_imagenes_limpias"] for r in res.values()]))
        tuning.append({**dict(zip(keys, combo)), "youden_medio": round(score, 4)})
        print(dict(zip(keys, combo)), f"Youden={score:.3f}")
        if score > best_score:
            best, best_score = params, score

    test = prepare("test")
    result = evaluate(test, best)
    report = {
        "tipo": "validación sintética (manchas pintadas sobre imágenes limpias de los grupos de prueba)",
        "advertencia": "No mide el desempeño con defectos reales; requiere un conjunto etiquetado del mercado.",
        "parametros_elegidos": {k: best[k] for k in keys},
        "ajuste_en_entrenamiento": tuning,
        "prueba_por_producto": result,
    }
    path = BACKEND / "models" / "metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    metrics["anomalias"] = report
    path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"parametros": report["parametros_elegidos"], "prueba": result}, indent=2, ensure_ascii=False))
    if report["parametros_elegidos"] != {k: DEFAULT_PARAMS[k] for k in keys}:
        print("NOTA: actualice DEFAULT_PARAMS en app/vision/anomalies.py con los parámetros elegidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
