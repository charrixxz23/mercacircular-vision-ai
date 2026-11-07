# Requisitos y casos de uso

Estado: ✅ implementado y probado · 🟡 simulado/rotulado · ⏳ trabajo futuro.

## Requisitos funcionales

| ID | Requisito | Estado | Dónde |
|---|---|---|---|
| RF-01 | Registrar lotes con ID único, producto, comerciante, área, fecha, peso, observaciones | ✅ | `/lotes/nuevo`, `POST /api/lots` |
| RF-02 | Buscar y filtrar lotes por texto, estado, producto, área y origen de los datos | ✅ | `/lotes` |
| RF-03 | Edición controlada con responsable y motivo; sin edición de lotes cerrados | ✅ | Ficha del lote, `PATCH` |
| RF-04 | Capturar foto con cámara (webcam o teléfono) o cargar archivo | ✅ | `/inspeccion` |
| RF-05 | Validar la imagen (formato, tamaño, resolución, nitidez, exposición, encuadre) | ✅ | `vision/quality.py` |
| RF-06 | Identificar el producto con un modelo entrenado y mostrar su probabilidad | ✅ | `vision/classifier.py` |
| RF-07 | Detectar indicios de deterioro exterior y localizarlos en la imagen | ✅ (heurístico) | `vision/anomalies.py` |
| RF-08 | Distinguir siempre modo IA real y modo demostrativo | ✅ / 🟡 | Insignias, avisos, campo `mode` |
| RF-09 | Recomendar acciones con reglas explícitas y sus razones | ✅ | `services/rules.py` |
| RF-10 | Registrar la decisión humana con responsable, rol, kg y notas | ✅ | Formulario de decisión |
| RF-11 | Restringir la donación a roles autorizados con confirmación explícita | ✅ | `services/status.py` |
| RF-12 | Línea de tiempo con cada evento y su responsable | ✅ | Ficha del lote |
| RF-13 | QR que abre la ficha del lote; etiqueta imprimible | ✅ | Ficha del lote |
| RF-14 | Dashboard calculado desde la base de datos | ✅ | `/`, `GET /api/dashboard` |
| RF-15 | Reportes por período con comparación y descarga CSV/PDF | ✅ | `/reportes` |
| RF-16 | Recorrido guiado de 10 pasos con funciones reales | ✅ | «Explorar MercaCircular» |
| RF-17 | Datos demostrativos estables y rotulados | 🟡 | `demo-data/seed.json` |
| RF-18 | Restablecer la demostración | ✅ | Acerca del proyecto |
| RF-19 | Agregar productos nuevos sin cambiar código | ✅ (por base de datos) | tabla `products` |
| RF-20 | Detección de enfermedades o frescura interna | ⏳ | — |
| RF-21 | Usuarios con inicio de sesión y permisos | ⏳ | El responsable se escribe en cada acción |

## Requisitos no funcionales

| ID | Requisito | Cómo se cumple |
|---|---|---|
| RNF-01 | Ejecutable en Windows sin servicios pagos | Python + Node, SQLite, inferencia en CPU; scripts PowerShell |
| RNF-02 | Persistencia tras reiniciar | SQLite en archivo; prueba `test_data_persists_after_restart` |
| RNF-03 | Responsive (móvil y escritorio) | Tailwind; verificado a 390 px sin desplazamiento horizontal |
| RNF-04 | Accesibilidad | Contraste AA, foco visible, etiquetas, `aria-*`, salto al contenido, movimiento reducido |
| RNF-05 | Modo claro y oscuro | Variables CSS por tema |
| RNF-06 | Tiempo de análisis | ≈ 20–90 ms por imagen en CPU (campo `processing_ms`) |
| RNF-07 | Privacidad | Las fotos se re-codifican sin metadatos EXIF; sin servicios externos |
| RNF-08 | Seguridad básica | Validación de tipo y tamaño, nombres de archivo generados, sin *pickle*, consultas ORM |
| RNF-09 | Trazabilidad | Todo cambio genera un evento; decisiones y análisis no se editan |
| RNF-10 | Portabilidad de base de datos | SQLAlchemy con tipos genéricos; PostgreSQL por `DATABASE_URL` |
| RNF-11 | Integridad académica | Métricas reales en `metrics.json`; modo demo rotulado; sin regiones inventadas |

## Actores

- **Operador(a) de recepción:** registra lotes y pesos.
- **Inspector(a) de calidad / Responsable de inocuidad:** fotografía, analiza y decide; únicos que
  pueden confirmar una donación.
- **Coordinador(a) comercial / Supervisor(a) de nave:** revisión comercial y disposición de residuos.
- **Analista o docente:** consulta indicadores, reportes y la ficha del modelo.

## Casos de uso

### CU-01 Registrar un lote de excedentes
1. El operador abre *Lotes → Registrar lote*, elige producto, comerciante, área, procedencia y cantidad.
2. El peso puede quedar pendiente. 3. El sistema asigna `MC-AAAA-NNNN`, estado *Registrado*, y crea el evento.
**Alternativo:** lote rápido desde *Inspección* (solo producto).

### CU-02 Inspeccionar con visión artificial
1. El inspector elige el lote, toma o carga una foto. 2. Ejecuta el **modo IA real**.
3. El sistema valida la imagen, segmenta, identifica y busca manchas; guarda la imagen anotada.
4. El lote pasa a *Inspeccionado* y se muestra la recomendación.
**Excepciones:** imagen inválida (415), demasiado grande (413), producto no visible o desenfocado →
recomendación *Solicitar una nueva imagen*.

### CU-03 Demostrar el flujo sin modelo
Igual que CU-02 pero eligiendo un **escenario demostrativo**. El resultado se rotula como tal, no tiene
regiones ni probabilidades y la foto (si existe) se guarda sin analizar.

### CU-04 Decidir el destino
1. Un responsable revisa la recomendación y sus razones. 2. Elige la acción, escribe su nombre y rol.
3. Para cerrar, indica los kg (≤ peso del lote). 4. Para **donar**, debe tener rol autorizado y marcar
la confirmación de evaluación de aptitud. 5. El sistema registra si siguió la recomendación.

### CU-05 Consultar la trazabilidad
Desde la lista, el panel o escaneando el QR, se abre la ficha: estado, datos, fotos, inspecciones,
decisiones y línea de tiempo con responsables.

### CU-06 Generar reportes
Elegir un período; el sistema lo compara con el anterior y permite descargar CSV y PDF.

### CU-07 Recorrer la demo guiada
*Explorar MercaCircular* ejecuta CU-01 → CU-02 → CU-04 → CU-05 con acciones reales y vuelve al panel.
