"""Pruebas del módulo de visión: segmentación, calidad, manchas, clasificador y pipeline."""

from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from app.vision import anomalies, features, quality
from app.vision.classifier import ProductClassifier
from app.vision.pipeline import analyze, decode
from app.vision.segmentation import fill_holes, segment
from conftest import BACKEND, SAMPLES, synthetic_fruit

MODEL = BACKEND / "models" / "product_classifier_v1.json"


def test_segmentation_finds_centered_fruit():
    seg = segment(synthetic_fruit())
    assert seg.bbox is not None
    expected = np.pi * (320 * 0.3) ** 2 / 320 ** 2
    assert abs(seg.coverage - expected) < 0.05
    assert seg.border_touch == 0


def test_segmentation_empty_image_has_no_object():
    seg = segment(np.full((200, 200, 3), 180, np.uint8))
    assert seg.bbox is None and seg.coverage == 0


def test_fill_holes_handles_object_touching_corner():
    m = np.zeros((50, 50), np.uint8)
    cv2.rectangle(m, (0, 0), (30, 30), 255, 3)  # anillo que toca la esquina (0, 0)
    filled = fill_holes(m)
    assert filled[15, 15] == 255      # el hueco interior se rellena
    assert filled[45, 45] == 0        # el fondo exterior no


def test_quality_flags_blurred_image():
    sharp = synthetic_fruit()
    rng = np.random.default_rng(0)
    sharp = np.clip(sharp.astype(int) + rng.integers(-12, 12, sharp.shape), 0, 255).astype(np.uint8)  # textura
    blurred = cv2.GaussianBlur(sharp, (0, 0), 6)
    s_sharp = quality.sharpness(cv2.cvtColor(sharp, cv2.COLOR_BGR2GRAY), segment(sharp).main_mask)
    s_blur = quality.sharpness(cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY), segment(blurred).main_mask)
    assert s_blur < s_sharp
    checks = {c.code: c for c in quality.assess(blurred, segment(blurred))}
    assert checks["nitidez"].status == "error"


def test_quality_flags_too_small_and_dark():
    small = cv2.resize(synthetic_fruit(), (50, 50))
    assert quality.summarize(quality.assess(small, segment(small))) == "insuficiente"
    dark = (synthetic_fruit(color=(20, 20, 40)) * 0.15).astype(np.uint8)
    checks = quality.assess(dark, segment(dark))
    assert quality.summarize(checks) == "insuficiente"


def test_anomaly_detector_localizes_spots_and_ignores_shading():
    clean = synthetic_fruit()
    regions, frac, _ = anomalies.detect(clean, segment(clean).mask)
    assert regions == [] and frac == 0          # el sombreado suave no es una mancha

    spots = [(140, 150, 14), (190, 185, 12)]
    dirty = synthetic_fruit(spots=spots)
    regions, frac, _ = anomalies.detect(dirty, segment(dirty).mask)
    assert len(regions) == 2
    for x, y, _ in spots:  # cada mancha real queda dentro de alguna región devuelta
        assert any(r.x <= x <= r.x + r.w and r.y <= y <= r.y + r.h for r in regions)
    assert 0 < frac < 0.2


def test_features_vector_shape_and_scale_invariance():
    img = synthetic_fruit()
    v1 = features.extract(img, segment(img).main_mask)
    big = cv2.resize(img, None, fx=2, fy=2)
    v2 = features.extract(big, segment(big).main_mask)
    assert v1.shape == (len(features.FEATURE_NAMES),)
    assert np.allclose(v1[:40], v2[:40], atol=0.05)   # histogramas de color casi iguales


@pytest.mark.skipif(not MODEL.exists(), reason="modelo no entrenado")
def test_classifier_numpy_inference_is_a_probability_distribution():
    clf = ProductClassifier.load(MODEL)
    img = synthetic_fruit()
    p = clf.predict_proba(features.extract(img, segment(img).main_mask))
    assert p.shape == (1, len(clf.classes))
    assert np.isclose(p.sum(), 1.0) and (p >= 0).all()


@pytest.mark.skipif(not MODEL.exists(), reason="modelo no entrenado")
def test_classifier_on_held_out_samples():
    """Imágenes de ejemplo de grupos de PRUEBA: tomate y banano se reconocen; la papa queda incierta o mal clasificada (limitación documentada)."""
    clf = ProductClassifier.load(MODEL)
    meta = json.loads((SAMPLES / "samples.json").read_text(encoding="utf-8"))
    results = {}
    for item in meta["imagenes"]:
        img = cv2.imread(str(SAMPLES / item["archivo"]))
        r, _ = analyze(img, item["producto"], clf)
        results[item["archivo"]] = r
    assert results["tomate_bandeja.jpg"]["identification"]["predicted"] == "tomate"
    assert results["banano_bandeja.jpg"]["identification"]["predicted"] == "banano"
    assert results["tomate_desenfocado.jpg"]["quality"]["summary"] == "insuficiente"
    assert results["tomate_manchas_sinteticas.jpg"]["anomalies"]["count"] >= 1
    assert results["tomate_bandeja.jpg"]["anomalies"]["count"] == 0


def test_pipeline_without_model_still_runs_quality_and_anomalies():
    img = synthetic_fruit(spots=[(150, 150, 15)])
    result, annotated = analyze(img, "tomate", None)
    assert result["identification"]["available"] is False
    assert result["anomalies"]["available"] is True and result["anomalies"]["count"] == 1
    assert annotated.shape == img.shape


def test_pipeline_reports_no_object():
    result, _ = analyze(np.full((300, 300, 3), 128, np.uint8), "tomate", None)
    assert result["quality"]["summary"] == "insuficiente"
    assert result["anomalies"]["available"] is False


def test_decode_rejects_non_images():
    with pytest.raises(ValueError):
        decode(b"esto no es una imagen")


def test_regions_scaled_back_to_original_resolution():
    img = cv2.resize(synthetic_fruit(spots=[(150, 150, 15)]), (1600, 1600))
    result, _ = analyze(img, "tomate", None)
    r = result["anomalies"]["regions"][0]
    assert 600 < r["x"] + r["w"] / 2 < 900 and 600 < r["y"] + r["h"] / 2 < 900   # ≈ (750, 750)
