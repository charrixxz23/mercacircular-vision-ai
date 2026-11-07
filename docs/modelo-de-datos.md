# Modelo de datos

Definido en `backend/app/models.py` (SQLAlchemy 2). Esquema SQL de referencia: `database/schema.sql`.
Fechas en UTC; la interfaz las muestra en hora de Panamá.

```mermaid
erDiagram
  products ||--o{ lots : "producto"
  merchants ||--o{ lots : "comerciante"
  areas ||--o{ lots : "área/nave"
  lots ||--o{ lot_images : "evidencia"
  lots ||--o{ inspections : "análisis"
  lots ||--o{ decisions : "decisiones humanas"
  lots ||--o{ lot_events : "trazabilidad"
  lot_images |o--o{ inspections : "imagen analizada"
  inspections |o--o{ decisions : "recomendación vigente"

  products { int id PK  string code UK  string name  string color  string model_label  bool active }
  merchants { int id PK  string name UK  bool is_demo }
  areas { int id PK  string name UK }
  lots {
    int id PK
    string code UK "MC-2026-0001 / MC-D-0001"
    int product_id FK
    int merchant_id FK
    int area_id FK
    string origin "procedencia"
    int quantity
    string quantity_unit
    float weight_kg "puede quedar pendiente"
    string status
    string destination "comercializado | donacion | residuos"
    float recovered_kg "confirmado por persona"
    float waste_kg "confirmado por persona"
    bool is_demo
    datetime created_at
    datetime inspected_at
    datetime decided_at
    datetime closed_at
  }
  lot_images { int id PK  int lot_id FK  string filename  string source  int width  int height  string sha256 }
  inspections {
    int id PK
    int lot_id FK
    int image_id FK
    string mode "ia | demo"
    string scenario
    string model_version
    string declared_product
    string predicted_product
    float prediction_score
    string quality_summary
    int anomaly_count
    float affected_pct
    json incidents
    json result "resultado completo"
    json recommendation "salida del motor de reglas"
    string annotated_filename
    bool is_demo
  }
  decisions {
    int id PK
    int lot_id FK
    int inspection_id FK
    string action
    string recommendation_code
    bool followed_recommendation
    string actor
    string role
    float kg
    string from_status
    string to_status
    bool is_demo
  }
  lot_events { int id PK  int lot_id FK  string type  string title  string actor  string from_status  string to_status  json payload  datetime created_at }
  app_meta { string key PK  string value }
```

## Notas de diseño

- **Inmutabilidad práctica de la evidencia.** Las inspecciones y decisiones no se editan ni borran
  desde la API; los cambios del lote se registran como eventos con el valor anterior y el nuevo.
- **Recomendación guardada tal como se emitió** (`inspections.recommendation`). La ficha solo oculta
  la razón R07 si el peso se registró después.
- **Separación de magnitudes.** `weight_kg` (entrada), `recovered_kg` y `waste_kg` (confirmados por
  una persona) son columnas distintas; los indicadores nunca derivan uno de otro.
- **Datos demostrativos** marcados con `is_demo` en lotes, inspecciones, decisiones y comerciantes.
- **Productos ampliables.** Agregar un producto es una fila en `products`. Si su `model_label` no es
  una clase del modelo, la identificación se muestra solo como orientativa y no genera la regla R02.
