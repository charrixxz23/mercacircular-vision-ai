"""Compara familias de modelos con la misma partición por grupos (≈ 3 min en CPU).

    python -m ml.compare_models

Reproduce la tabla «Comparación de familias de modelos» de docs/dataset-y-validacion.md.
La selección se hace por la validación cruzada LOGO sobre entrenamiento; la columna de
prueba se muestra solo como referencia.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.dataset import build  # noqa: E402
from ml.train import CLASSES, featurize  # noqa: E402

MODELS = {
    "Regresión logística (C=0.01)": make_pipeline(StandardScaler(), LogisticRegression(C=0.01, max_iter=5000, class_weight="balanced")),
    "SVM RBF": make_pipeline(StandardScaler(), SVC(C=1, class_weight="balanced")),
    "Red neuronal (32)": make_pipeline(StandardScaler(), MLPClassifier((32,), alpha=1.0, max_iter=2000, random_state=0)),
    "Red neuronal (64)": make_pipeline(StandardScaler(), MLPClassifier((64,), alpha=3.0, max_iter=2000, random_state=0)),
    "Bosque aleatorio": RandomForestClassifier(300, min_samples_leaf=5, class_weight="balanced", n_jobs=-1, random_state=0),
    "Gradient boosting": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, class_weight="balanced", random_state=0),
}


def main() -> int:
    X, y, g, sp, _, _ = featurize(build())
    tr, te = sp == "train", sp == "test"
    print(f"{'Modelo':32s} {'F1 LOGO-CV':>11s} {'Exact. prueba':>14s} {'F1 prueba':>10s}  sensibilidad por clase (prueba)")
    for name, model in MODELS.items():
        t0 = time.time()
        cv = cross_val_predict(model, X[tr], y[tr], groups=g[tr], cv=LeaveOneGroupOut(), n_jobs=-1)
        model.fit(X[tr], y[tr])
        pred = model.predict(X[te])
        rec = {c: round(float(np.mean(pred[y[te] == c] == c)), 2) for c in CLASSES}
        print(f"{name:32s} {f1_score(y[tr], cv, average='macro'):11.3f} {accuracy_score(y[te], pred):14.3f} "
              f"{f1_score(y[te], pred, average='macro'):10.3f}  {rec}  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
