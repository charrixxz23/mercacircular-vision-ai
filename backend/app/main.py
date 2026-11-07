"""Aplicación FastAPI de MercaCircular Vision AI.

Ejecutar (desde la carpeta backend):

    uvicorn app.main:app --reload --port 8000

Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import Database
from .routers.api import router
from .services import seed
from .services.inspections import VisionRuntime

DESCRIPTION = """
API del prototipo académico **MercaCircular Vision AI**: registro de lotes de excedentes agrícolas,
análisis visual (modo IA real con OpenCV + regresión logística, o modo demostrativo explícito),
recomendaciones basadas en reglas, decisiones humanas, trazabilidad, indicadores y reportes.

> Prototipo académico independiente desarrollado como caso de estudio para Merca Panamá.
> No representa un sistema oficial de la institución.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = app.state.db
        db.create_all()
        session = db.SessionLocal()
        try:
            seed.ensure_catalog(session, seed.load_seed(settings))
            session.commit()
            if settings.seed_demo_data:
                n = seed.seed_demo(session, settings, app.state.runtime)
                if n:
                    logging.getLogger("mercacircular").info("Datos demostrativos cargados: %s lotes", n)
        finally:
            session.close()
        yield
        db.engine.dispose()

    app = FastAPI(title="MercaCircular Vision AI", version="1.0.0", description=DESCRIPTION, lifespan=lifespan)
    app.state.settings = settings
    app.state.db = Database(settings.database_url)
    app.state.runtime = VisionRuntime.load(settings)

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)

    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
    samples = settings.demo_data_dir / "images"
    if samples.exists():
        app.mount("/samples", StaticFiles(directory=samples), name="samples")
    return app


app = create_app()
