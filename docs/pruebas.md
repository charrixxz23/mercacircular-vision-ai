# Estrategia y resultados de pruebas

Este documento distingue lo que se **ejecutó** durante el desarrollo de lo que **no se pudo ejecutar**.
Entorno de desarrollo: Linux x86-64, Python 3.13, Node.js 22, Chromium (Playwright).

## Cómo ejecutarlas

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

o por separado:

```powershell
cd backend;  .venv\Scripts\python -m pytest        # 32 pruebas
cd frontend; npm run typecheck; npm test            # TypeScript estricto + 5 pruebas vitest
```

## 1. Pruebas automatizadas incluidas

### Backend — `backend/tests` (pytest)

| Archivo | Qué verifica |
|---|---|
| `test_vision.py` (13) | Segmentación de una fruta centrada y de una imagen vacía; relleno de huecos cuando el objeto toca una esquina (regresión de un error real); rechazo de imágenes borrosas, pequeñas y oscuras; el detector de manchas **ignora el sombreado** y **localiza** dos manchas conocidas; invariancia de escala de las características; la inferencia en NumPy produce una distribución de probabilidad; clasificación de las imágenes de ejemplo de grupos de prueba; funcionamiento sin modelo; regiones reescaladas a la resolución original; rechazo de archivos que no son imágenes. |
| `test_rules.py` (7) | Reglas R01–R09: imagen insuficiente, anomalías con prioridad, sin anomalías, producto que no coincide, identificación incierta, clase poco fiable, peso pendiente, manchas naturales en banano, modo demostrativo; acciones disponibles por estado y restricciones de la donación. |
| `test_api.py` (12) | Flujo completo en modo IA (lote → foto → análisis → decisiones → cierre por donación) con verificación de roles, confirmación y kg; el dashboard refleja los cambios; el modo demostrativo no tiene regiones ni probabilidad; errores 400/404/409/415/422; edición controlada y evento de peso; búsqueda y filtros; CSV con BOM y PDF válido; ficha del modelo; **persistencia tras reiniciar la aplicación**; restablecimiento de la demo; estabilidad de los indicadores entre solicitudes. |

**Resultado ejecutado:** `32 passed` (también desde una copia limpia extraída del ZIP).

### Frontend — `frontend/tests` (vitest) y TypeScript

- Formato es-PA de kg, porcentajes, variaciones y duraciones.
- Definición del recorrido guiado: 10 pasos, cada uno con un elemento objetivo, rutas que usan el lote
  creado, y pasos con acción que esperan el evento que confirma que se completó.
- `tsc --noEmit` en modo estricto sobre todo el código.

**Resultado ejecutado:** `5 passed`; verificación de tipos sin errores; `next build` sin errores.

## 2. Verificación en navegador (ejecutada durante el desarrollo, no incluida como prueba automática)

Con backend y frontend reales (Chromium + Playwright), 18 comprobaciones, todas aprobadas:

| Escenario | Resultado |
|---|---|
| Recorrido «Explorar MercaCircular» de principio a fin (crear lote → imagen → análisis → peso → recomendación → decisión → estado → trazabilidad → panel) | ✅ cada paso avanzó con la acción real |
| El análisis IA del tomate con manchas sintéticas identificó «tomate» y marcó regiones | ✅ |
| Los indicadores del panel cambiaron tras el recorrido | ✅ |
| Registrar donación con rol «Coordinador(a) comercial» | ✅ rechazado con mensaje claro (HTTP 403) |
| Registrar donación con «Inspector(a) de calidad» + confirmación | ✅ lote cerrado como donación |
| Captura con cámara (dispositivo de video simulado por Chromium) y análisis | ✅ (el patrón de prueba se identificó como «otro» y se marcó como discrepancia, como corresponde) |
| Descarga del resumen PDF | ✅ |
| Búsqueda por código de lote | ✅ |
| Tema oscuro | ✅ revisado visualmente |
| Sin desplazamiento horizontal a 390 px en panel, inspección y ficha | ✅ (se corrigió un desbordamiento en la ficha detectado por esta prueba) |
| Consola del navegador | Sin errores, salvo el 403 esperado del intento de donación no autorizado |

Además, desde el ZIP extraído en una carpeta nueva: instalación con `scripts/setup.sh`, inicio con
`scripts/start.sh`, carga de las 8 páginas sin errores de consola, análisis IA desde la interfaz y
**persistencia verificada reiniciando el backend** (el lote creado y su inspección seguían ahí; los datos
demostrativos no se duplicaron).

## 3. Contenedor para la nube

La imagen Docker no se pudo construir en el entorno de desarrollo (sin acceso a Docker Hub). Se verificó
lo equivalente: el frontend compilado en modo *standalone* y el backend se colocaron con la misma
estructura de carpetas del `Dockerfile` y se arrancaron con el mismo `docker/start.sh`. Resultado: API
y web en un solo puerto, las 8 páginas cargan sin errores de consola, el análisis IA funciona desde la
interfaz y el consumo total fue ≈ 250 MB (uvicorn ≈ 144 MB, Next.js ≈ 106 MB). La construcción real de
la imagen se verifica en GitHub Actions (job *Imagen Docker*) en cada push.

## 4. Validación del modelo

Ver [`dataset-y-validacion.md`](dataset-y-validacion.md): partición por grupos, validación cruzada
*leave-one-group-out*, evaluación única en prueba, matriz de confusión, sensibilidad y falsos positivos
por clase, calibración, y validación sintética del detector de manchas.

## 5. Lo que NO se ejecutó

| Elemento | Motivo | Cómo verificarlo |
|---|---|---|
| Scripts **PowerShell** (`scripts\*.ps1`) | El entorno de desarrollo era Linux sin PowerShell disponible. Se revisaron a mano y su lógica equivale a `setup.sh`/`start.sh`, que sí se ejecutaron. | Ejecutar `scripts\setup.ps1` y `scripts\test.ps1` en Windows |
| Instalación en **Windows** | Sin máquina Windows disponible | Ídem |
| Cámara real de teléfono o webcam | Solo se probó el dispositivo simulado de Chromium | Abrir con `scripts\start.ps1 -Lan` desde un teléfono |
| Fotos reales del mercado | No hay imágenes reales ni autorización | Piloto (ver Trabajo futuro) |
| PostgreSQL | Solo se probó SQLite | `DATABASE_URL=postgresql+psycopg://…` |
| Rendimiento con miles de lotes | Los indicadores se calculan en Python sobre todos los lotes (adecuado para la demo) | Mover agregaciones a SQL antes de escalar |
