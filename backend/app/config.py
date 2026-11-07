"""Configuración por variables de entorno (ver ``.env.example`` en la raíz)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent

# .env en la raíz del proyecto (opcional). Las variables ya definidas tienen prioridad.
load_dotenv(ROOT_DIR / ".env", override=False)


def _path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    return p if p.is_absolute() else (ROOT_DIR / p).resolve()


@dataclass
class Settings:
    database_url: str = ""
    media_dir: Path = ROOT_DIR / "database" / "media"
    model_path: Path = BACKEND_DIR / "models" / "product_classifier_v1.json"
    metrics_path: Path = BACKEND_DIR / "models" / "metrics.json"
    demo_data_dir: Path = ROOT_DIR / "demo-data"
    cors_origins: list[str] = field(default_factory=list)
    max_upload_mb: float = 10.0
    seed_demo_data: bool = True
    allow_reset: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        db_file = ROOT_DIR / "database" / "mercacircular.db"
        return cls(
            database_url=os.getenv("DATABASE_URL") or f"sqlite:///{db_file.as_posix()}",
            media_dir=_path(os.getenv("MEDIA_DIR"), ROOT_DIR / "database" / "media"),
            model_path=_path(os.getenv("MODEL_PATH"), BACKEND_DIR / "models" / "product_classifier_v1.json"),
            metrics_path=_path(os.getenv("METRICS_PATH"), BACKEND_DIR / "models" / "metrics.json"),
            demo_data_dir=_path(os.getenv("DEMO_DATA_DIR"), ROOT_DIR / "demo-data"),
            cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()],
            max_upload_mb=float(os.getenv("MAX_UPLOAD_MB", "10")),
            seed_demo_data=os.getenv("SEED_DEMO_DATA", "true").lower() in {"1", "true", "yes", "si", "sí"},
            allow_reset=os.getenv("ALLOW_DEMO_RESET", "true").lower() in {"1", "true", "yes", "si", "sí"},
        )
