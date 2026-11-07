"""Entrena y evalúa el clasificador de producto.

    python -m ml.download_dataset   # una vez
    python -m ml.train              # ≈ 1–2 min en CPU

Pasos:
1. Arma la muestra por grupos (``splits.json``): ningún grupo está en entrenamiento y prueba a la vez.
2. Coloca cada fruta sobre un fondo aleatorio y la procesa con el MISMO pipeline de producción
   (segmentación → características).
3. Elige la regularización C con validación cruzada "dejando un grupo fuera" (LOGO) sobre entrenamiento.
4. Entrena el modelo final con todo el entrenamiento y lo evalúa UNA vez en prueba.
5. Exporta ``models/product_classifier_v1.json`` y ``models/metrics.json``.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.vision.features import FEATURE_NAMES, extract  # noqa: E402
from app.vision.quality import SHARPNESS_ERROR, SHARPNESS_WARN, sharpness  # noqa: E402
from app.vision.segmentation import segment  # noqa: E402
from ml.augment import composite  # noqa: E402
from ml.dataset import DEFAULT_DATA, build, load_splits  # noqa: E402

CLASSES = ["tomate", "banano", "papa", "otro"]
C_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
MIN_CONFIDENCE = 0.6
MODEL_VERSION = "mc-lr-1.0"


def featurize(samples):
    X, y, groups, splits, sharp, failures = [], [], [], [], [], 0
    for s in samples:
        img = cv2.imread(str(s.path))
        photo = composite(img, np.random.default_rng(s.seed))
        seg = segment(photo)
        if seg.bbox is None:
            failures += 1
            continue
        X.append(extract(photo, seg.main_mask))
        y.append(s.label)
        groups.append(s.group)
        splits.append(s.split)
        if s.split == "test":
            gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
            sharp.append([sharpness(cv2.GaussianBlur(gray, (0, 0), sig) if sig else gray, seg.main_mask) for sig in (0, 1.5, 2.5)])
    return np.array(X), np.array(y), np.array(groups), np.array(splits), np.array(sharp), failures


def ece(probs: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    conf = probs.max(axis=1)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (conf > lo) & (conf <= hi)
        if sel.any():
            total += sel.mean() * abs(correct[sel].mean() - conf[sel].mean())
    return float(total)


def per_class(y_true, y_pred) -> dict:
    p, r, f, sup = precision_recall_fscore_support(y_true, y_pred, labels=CLASSES, zero_division=0)
    out = {}
    for i, c in enumerate(CLASSES):
        negatives = y_true != c
        fpr = float(np.mean(y_pred[negatives] == c)) if negatives.any() else 0.0
        out[c] = {"precision": round(float(p[i]), 4), "sensibilidad": round(float(r[i]), 4), "f1": round(float(f[i]), 4),
                  "tasa_falsos_positivos": round(fpr, 4), "soporte": int(sup[i])}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=BACKEND / "models")
    args = ap.parse_args()
    t0 = time.time()

    samples = build(args.data)
    X, y, groups, splits, sharp, failures = featurize(samples)
    tr, te = splits == "train", splits == "test"
    print(f"Muestras: {tr.sum()} entrenamiento / {te.sum()} prueba · fallos de segmentación: {failures}")

    # ── Selección de C con validación cruzada dejando un grupo fuera ──────────
    logo = LeaveOneGroupOut()
    cv_scores = {}
    for C in C_GRID:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=5000, class_weight="balanced"))
        pred = cross_val_predict(model, X[tr], y[tr], groups=groups[tr], cv=logo, n_jobs=-1)
        cv_scores[C] = float(f1_score(y[tr], pred, average="macro"))
        print(f"  C={C:<5} F1 macro (LOGO-CV) = {cv_scores[C]:.4f}")
    best_c = max(cv_scores, key=cv_scores.get)

    # ── Modelo final y evaluación única en prueba ─────────────────────────────
    model = make_pipeline(StandardScaler(), LogisticRegression(C=best_c, max_iter=5000, class_weight="balanced"))
    model.fit(X[tr], y[tr])
    lr = model[-1]
    order = [list(lr.classes_).index(c) for c in CLASSES]
    probs = model.predict_proba(X[te])[:, order]
    pred = np.array(CLASSES)[probs.argmax(axis=1)]
    correct = pred == y[te]
    confident = probs.max(axis=1) >= MIN_CONFIDENCE

    per_group = {}
    for g in sorted(set(groups[te])):
        sel = groups[te] == g
        per_group[g] = {"clase": str(y[te][sel][0]), "n": int(sel.sum()), "exactitud": round(float(correct[sel].mean()), 4)}

    metrics = {
        "version": MODEL_VERSION,
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entorno": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "opencv": cv2.__version__},
        "dataset": load_splits()["dataset"],
        "particion": "por grupos (grabación completa en un solo lado); ver ml/splits.json",
        "muestras": {"entrenamiento": int(tr.sum()), "prueba": int(te.sum()), "fallos_segmentacion": failures,
                     "por_clase_prueba": {c: int((y[te] == c).sum()) for c in CLASSES},
                     "grupos_prueba": {c: load_splits()["clases"][c]["test"] for c in CLASSES}},
        "seleccion_modelo": {"metodo": "Leave-One-Group-Out sobre entrenamiento", "metrica": "F1 macro",
                             "resultados": {str(k): round(v, 4) for k, v in cv_scores.items()}, "C_elegido": best_c},
        "prueba": {
            "exactitud": round(float(correct.mean()), 4),
            "f1_macro": round(float(f1_score(y[te], pred, average="macro")), 4),
            "por_clase": per_class(y[te], pred),
            "matriz_confusion": {"etiquetas": CLASSES, "filas_real_columnas_predicho": confusion_matrix(y[te], pred, labels=CLASSES).tolist()},
            "calibracion": {"ece_10_bins": round(ece(probs, correct), 4),
                            "brier": round(float(np.mean(np.sum((probs - (np.array(CLASSES)[:, None] == y[te]).T) ** 2, axis=1))), 4)},
            "umbral_confianza": {"umbral": MIN_CONFIDENCE, "cobertura": round(float(confident.mean()), 4),
                                 "exactitud_sobre_umbral": round(float(correct[confident].mean()), 4) if confident.any() else None},
            "por_grupo": per_group,
        },
        "nitidez": {
            "descripcion": "Varianza del Laplaciano normalizada, medida en imágenes de prueba nítidas y con desenfoque gaussiano.",
            "umbral_error": SHARPNESS_ERROR, "umbral_advertencia": SHARPNESS_WARN,
            "percentiles_5_50_95": {f"sigma_{s}": np.percentile(sharp[:, i], [5, 50, 95]).round(3).tolist() for i, s in enumerate((0, 1.5, 2.5))},
            "rechazadas_como_error": {f"sigma_{s}": round(float(np.mean(sharp[:, i] < SHARPNESS_ERROR)), 4) for i, s in enumerate((0, 1.5, 2.5))},
        },
        "duracion_s": round(time.time() - t0, 1),
    }

    exported = {
        "version": MODEL_VERSION,
        "tipo": "Regresión logística multinomial (scikit-learn) sobre 63 características OpenCV",
        "classes": CLASSES,
        "feature_names": FEATURE_NAMES,
        "min_confidence": MIN_CONFIDENCE,
        "scaler_mean": model[0].mean_.tolist(),
        "scaler_scale": model[0].scale_.tolist(),
        "coef": lr.coef_[order].tolist(),
        "intercept": lr.intercept_[order].tolist(),
        "dataset": metrics["dataset"],
        "licencia_pesos": "CC BY-SA 4.0 (derivados de Fruits-360)",
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "product_classifier_v1.json").write_text(json.dumps(exported), encoding="utf-8")
    existing = json.loads((args.out / "metrics.json").read_text(encoding="utf-8")) if (args.out / "metrics.json").exists() else {}
    existing["clasificador"] = metrics
    (args.out / "metrics.json").write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(metrics["prueba"], indent=2, ensure_ascii=False))
    print(f"Modelo guardado en {args.out}. Tiempo: {metrics['duracion_s']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
