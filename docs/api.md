# API REST

Base: `http://127.0.0.1:8000`. Documentación interactiva generada por FastAPI: **`/docs`** (Swagger) y `/redoc`.
Desde el frontend se usan las mismas rutas a través de `http://localhost:3000/api/...`.

Los errores devuelven `{"detail": "mensaje en español"}` con el código HTTP correspondiente
(400 dato inválido, 403 rol no autorizado, 404 no existe, 409 estado no permite la acción,
413 imagen demasiado grande, 415 archivo no es imagen, 422 validación de esquema).

## Sistema

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado y si el modelo está cargado |
| GET | `/api/catalog` | Productos, comerciantes, áreas, estados, destinos, roles, acciones, escenarios |
| GET | `/api/model` | Ficha del modelo: metadatos, métricas, reglas, limitaciones, escenarios, imágenes de ejemplo |
| POST | `/api/demo/reset` | Borra todos los lotes y recarga la demostración (`ALLOW_DEMO_RESET`) |

## Lotes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/lots` | Lista. Filtros: `q`, `status` (separados por coma), `product`, `area_id`, `demo`, `desde`, `hasta`, `limit`, `offset` |
| POST | `/api/lots` | Registra un lote |
| GET | `/api/lots/{code}` | Ficha completa: imágenes, inspecciones, decisiones, línea de tiempo, acciones disponibles |
| PATCH | `/api/lots/{code}` | Edición controlada (requiere `actor`; queda en la trazabilidad) |
| POST | `/api/lots/{code}/status` | `{"action":"marcar_pendiente","actor":"…"}` |
| GET | `/api/lots/{code}/timeline` | Solo los eventos |

```json
POST /api/lots
{ "product_id": 1, "merchant_id": 2, "area_id": 2, "origin": "Coclé", "quantity": 12,
  "quantity_unit": "cajas", "weight_kg": 240, "observations": "Sin comprador", "registered_by": "María G." }
```

Reglas de edición: un lote cerrado no se edita (409); el producto no cambia si ya hay inspecciones (409).

## Inspección

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/lots/{code}/images` | `multipart/form-data`: `file`, `source` (`camera`/`upload`/`sample`), `actor`. Máx. 10 MB; se re-codifica a JPEG |
| POST | `/api/lots/{code}/inspections` | `{"mode":"ia","image_id":5}` o `{"mode":"demo","scenario_id":"manchas_leves"}` |

Respuesta de una inspección (resumida):

```json
{
  "id": 81, "mode": "ia", "model_version": "mc-lr-1.0",
  "predicted_product": "tomate", "prediction_score": 0.9156, "anomaly_count": 2, "affected_pct": 5.79,
  "incidents": ["manchas_oscuras"],
  "result": {
    "quality": {"summary": "buena", "checks": [{"code": "nitidez", "status": "ok", "value": 1.26, "message": "Imagen nítida."}]},
    "identification": {"declared": "tomate", "predicted": "tomate", "probability": 0.9156, "reliable": true},
    "anomalies": {"count": 2, "affected_pct": 5.79, "regions": [{"x": 91, "y": 98, "w": 21, "h": 19, "area_pct": 3.34}]},
    "observations": ["…"], "limitations": ["…"]
  },
  "recommendation": {"code": "revision_humana", "title": "Revisión humana de anomalías",
                     "suggested_actions": ["enviar_revision_comercial", "enviar_evaluacion_donacion", "enviar_gestion_residuos"],
                     "reasons": [{"rule": "R05", "level": "advertencia", "text": "…"}], "requires_human_confirmation": true},
  "annotated_url": "/media/lots/MC-2026-0001/ab12cd34ef56_analisis.jpg"
}
```

En modo demostrativo `regions` siempre es `[]`, no hay probabilidad y `limitations` incluye el aviso.

## Decisiones humanas

`POST /api/lots/{code}/decisions`

```json
{ "action": "confirmar_donacion", "actor": "Ana Ríos", "role": "Inspector(a) de calidad",
  "kg": 200, "confirm": true, "notes": "Apto tras revisión presencial" }
```

| Acción | Desde | Hacia | Requisitos |
|---|---|---|---|
| `marcar_pendiente` | registrado | pendiente_inspeccion | — |
| `solicitar_nueva_imagen` | inspeccionado | pendiente_inspeccion | — |
| `enviar_revision_comercial` | inspeccionado | revision_comercial | — |
| `enviar_evaluacion_donacion` | inspeccionado, revision_comercial | evaluacion_donacion | — |
| `enviar_gestion_residuos` | inspeccionado, revision_comercial, evaluacion_donacion | gestion_residuos | — |
| `confirmar_comercializacion` | revision_comercial | cerrado (comercializado) | peso registrado, `kg` ≤ peso |
| `confirmar_donacion` | evaluacion_donacion | cerrado (donación) | rol autorizado, `confirm: true`, `kg` ≤ peso |
| `confirmar_residuos` | gestion_residuos | cerrado (residuos) | peso registrado, `kg` ≤ peso |

Roles autorizados para donar: *Inspector(a) de calidad*, *Responsable de inocuidad*.

## Indicadores y reportes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/dashboard?weeks=12` | KPIs, lotes por estado y producto, tendencia semanal, incidencias, destinos, historial |
| GET | `/api/reports/summary?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` | Período vs. período anterior de igual duración |
| GET | `/api/reports/summary.csv` · `.pdf` | Mismo reporte descargable |
| GET | `/api/reports/lotes.csv` · `inspecciones.csv` · `decisiones.csv` | Tablas completas (UTF-8 con BOM, abre bien en Excel) |

## Archivos

| Ruta | Contenido |
|---|---|
| `/media/lots/{code}/…jpg` | Fotos subidas y sus versiones anotadas |
| `/samples/…jpg` | Imágenes de ejemplo de `demo-data/images` |
