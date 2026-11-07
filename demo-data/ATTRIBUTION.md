# Atribución de imágenes y datos

## Fruits-360

- **Autor:** Mihai Oltean
- **Fuente:** https://github.com/fruits-360/fruits-360-100x100 (rama 100x100)
- **Licencia:** Creative Commons Atribución-CompartirIgual 4.0 Internacional (CC BY-SA 4.0) — https://creativecommons.org/licenses/by-sa/4.0/
- **Cita:** Mihai Oltean, *Fruits-360 dataset*, 2017-.

### Material derivado incluido en este repositorio

| Archivo | Imagen original (grupo de prueba) | Cambios |
|---|---|---|
| `images/tomate_bandeja.jpg` | Tomato 3 | Fruta colocada sobre un fondo de bandeja generado |
| `images/tomate_manchas_sinteticas.jpg` | Tomato 3 | Fondo de bandeja + dos manchas oscuras **artificiales** |
| `images/tomate_desenfocado.jpg` | Tomato 3 | Fondo de bandeja + desenfoque gaussiano |
| `images/banano_bandeja.jpg` | Banana 3 | Fruta colocada sobre un fondo de bandeja |
| `images/papa_bandeja.jpg` | Potato Red 2 | Fruta colocada sobre un fondo de bandeja |
| `backend/models/product_classifier_v1.json` | Subconjunto descrito en `backend/ml/splits.json` | Parámetros de un modelo entrenado con esas imágenes |

Estas obras derivadas se distribuyen bajo la misma licencia **CC BY-SA 4.0**. El licenciante original
no respalda este proyecto.

Las imágenes completas del conjunto de datos **no** se incluyen: `backend/ml/download_dataset.py` las
descarga del repositorio oficial cuando se quiere reentrenar.
