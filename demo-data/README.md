# Datos demostrativos

Todo lo que hay aquí es **sintético o derivado de un conjunto de datos público**. Nada proviene de Merca Panamá.

| Archivo | Contenido | Origen |
|---|---|---|
| `seed.json` | 80 lotes ficticios con 12 semanas de historial (inspecciones en modo demostrativo y decisiones) | Generado por `scripts/generate_demo_seed.py` con semilla fija |
| `scenarios.json` | Escenarios del **modo demostrativo** (resultados predefinidos, sin regiones ni probabilidades) | Escrito a mano |
| `images/*.jpg` | Imágenes de prueba para el **modo IA real** | Derivadas de Fruits-360 (CC BY-SA 4.0), ver `ATTRIBUTION.md` |
| `images/samples.json` | Descripción de cada imagen, su grupo de origen y los cambios realizados | Generado por `backend/ml/make_demo_images.py` |

## Cómo se cargan

Al iniciar, el backend reproduce `seed.json` con las mismas reglas de negocio de la app (estados,
decisiones, trazabilidad). Las fechas se calculan relativas al día de la carga y luego **quedan fijas
en la base de datos**: refrescar la página no cambia ningún número. Los registros llevan
`is_demo = true` y la interfaz los rotula como *Demostrativo*.

Comerciantes («Agro Demo Los Valles», …) y personas («A. Ríos (ficticia)», …) son inventados.
