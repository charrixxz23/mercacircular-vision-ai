"""Fixtures: cada prueba usa una base SQLite y una carpeta de medios temporales."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

ROOT = BACKEND.parent
SAMPLES = ROOT / "demo-data" / "images"


def make_settings(tmp: Path, seed: bool = True) -> Settings:
    base = Settings.from_env()
    base.database_url = f"sqlite:///{(tmp / 'test.db').as_posix()}"
    base.media_dir = tmp / "media"
    base.seed_demo_data = seed
    base.cors_origins = []
    return base


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def empty_client(tmp_path: Path):
    """API sin datos demostrativos (solo catálogo)."""
    with TestClient(create_app(make_settings(tmp_path, seed=False))) as c:
        yield c


def synthetic_fruit(color=(30, 30, 200), spots: list[tuple[int, int, int]] | None = None, size: int = 320, blur: float = 0) -> np.ndarray:
    """Fruta redonda sintética con sombreado suave sobre fondo gris; ``spots`` = (x, y, radio)."""
    img = np.full((size, size, 3), (205, 205, 200), np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c, r = size / 2, size * 0.3
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    inside = d < r
    shade = 1.0 - 0.25 * ((xx - c * 0.8) / (2 * r)) - 0.15 * ((yy - c * 0.8) / (2 * r))
    for ch in range(3):
        img[..., ch][inside] = color[ch] * shade[inside]
    for (x, y, rad) in spots or []:
        spot = (np.sqrt((xx - x) ** 2 + (yy - y) ** 2) < rad) & inside
        img[spot] = img[spot] * 0.3 + np.array([20, 30, 45]) * 0.7
    out = np.clip(img, 0, 255).astype(np.uint8)
    if blur:
        out = cv2.GaussianBlur(out, (0, 0), blur)
    return out


def jpeg(img: np.ndarray) -> bytes:
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return enc.tobytes()
