"""Clasificador de producto: regresión logística multinomial.

El modelo se entrena con scikit-learn (``backend/ml/train.py``) y se exporta a
JSON (medias, escalas, coeficientes). La inferencia se hace aquí con NumPy:

    z = (x - media) / escala
    p = softmax(W · z + b)

Así la demo no depende de la versión de scikit-learn ni carga archivos pickle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .features import FEATURE_NAMES


@dataclass
class Prediction:
    label: str
    probability: float
    probabilities: dict[str, float]


class ProductClassifier:
    def __init__(self, data: dict):
        if data.get("feature_names") != FEATURE_NAMES:
            raise ValueError("El modelo fue entrenado con otro conjunto de características.")
        self.version: str = data["version"]
        self.classes: list[str] = data["classes"]
        self.mean = np.asarray(data["scaler_mean"], dtype=np.float64)
        self.scale = np.asarray(data["scaler_scale"], dtype=np.float64)
        self.coef = np.asarray(data["coef"], dtype=np.float64)
        self.intercept = np.asarray(data["intercept"], dtype=np.float64)
        self.min_confidence: float = float(data.get("min_confidence", 0.6))
        self.metadata: dict = {k: v for k, v in data.items() if k not in {"scaler_mean", "scaler_scale", "coef", "intercept"}}

    @classmethod
    def load(cls, path: str | Path) -> "ProductClassifier":
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        z = (np.atleast_2d(x) - self.mean) / self.scale
        logits = z @ self.coef.T + self.intercept
        logits -= logits.max(axis=1, keepdims=True)
        e = np.exp(logits)
        return e / e.sum(axis=1, keepdims=True)

    def predict(self, x: np.ndarray) -> Prediction:
        p = self.predict_proba(x)[0]
        i = int(np.argmax(p))
        return Prediction(self.classes[i], float(p[i]), {c: round(float(v), 4) for c, v in zip(self.classes, p)})
