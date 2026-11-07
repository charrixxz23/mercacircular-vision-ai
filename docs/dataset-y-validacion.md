# Dataset, entrenamiento y validación

Todas las cifras de este documento salen de `backend/models/metrics.json`, generado por
`python -m ml.train` y `python -m ml.evaluate_anomalies` (ver `scripts/train-model.ps1`).

## 1. Datos

**Fruits-360** (Mihai Oltean, rama 100×100, licencia CC BY-SA 4.0): fotos de frutas y vegetales que
giran frente a una cámara sobre papel blanco; cada carpeta es **una grabación** (≈ 300–1000 fotogramas
casi idénticos de la misma pieza).

| Clase del modelo | Carpetas (grupos) usadas |
|---|---|
| tomate | 15 grabaciones: Tomato 1–5, 7–11, Heart 1, Maroon 1–2, Cherry Red 1–2 |
| banano | Banana 1–4, Banana Lady Finger 1 |
| papa | Potato Red 1, Potato Red 2, Potato White 1 |
| otro | 25 grabaciones de otras frutas/vegetales (manzana, pimentón, cebolla, mango, camote…) |

La clase **otro** permite responder «no es ninguno de los tres» en lugar de forzar una de ellas.
El camote (*Potato Sweet*) se etiqueta como «otro» porque no es papa. Se excluyen el banano rojo y los
tomates amarillos por no ser representativos del producto comercializado en Panamá.

**Etiquetado:** la etiqueta es la carpeta de origen (etiquetado del propio dataset). No hay etiquetas
de defectos.

### Estrategia para conseguir datos reales (trabajo futuro)

1. Protocolo de captura en el mercado (con autorización): bandeja de color uniforme, luz difusa,
   1–3 fotos por lote, distintas caras del producto.
2. Etiquetado por personal de calidad con dos niveles: producto y estado (sin defecto / defecto
   superficial leve / deterioro extenso), dibujando las regiones de defecto.
3. Conjuntos públicos con licencia compatible para preentrenar la detección de defectos (revisar la
   licencia de cada uno antes de usarlo; muchos conjuntos de Kaggle son solo para uso no comercial).
4. Partición **por lote y por día de captura** para evitar fuga (ver abajo).

## 2. Partición sin fuga de información

Los fotogramas de una misma grabación son prácticamente la misma imagen. Si se repartieran al azar,
el modelo «vería» en entrenamiento casi las mismas fotos que en prueba y las métricas serían irreales.
Por eso la partición es **por grupo** (`backend/ml/splits.json`): una grabación completa va a
entrenamiento **o** a prueba, nunca a ambos. Las carpetas Training/Test originales de Fruits-360 se
unen dentro de cada grupo porque provienen de la misma grabación.

| | Entrenamiento | Prueba |
|---|---|---|
| Imágenes | 2 888 | 1 200 (300 por clase) |
| Grupos tomate | 11 | Tomato 3, Tomato 9, Tomato Maroon 2, Tomato Cherry Red 2 |
| Grupos banano | 4 | Banana 3 |
| Grupos papa | 2 | Potato Red 2 |
| Grupos otro | 19 | Apple Red 1, Mango 1, Onion White 1, Orange 1, Peach 1, Plum 1 |

**Validación:** la regularización se eligió con *Leave-One-Group-Out* (cada grupo de entrenamiento
se deja fuera una vez) sobre el conjunto de entrenamiento. El conjunto de prueba se evaluó **una vez**
con el modelo final.

**Acercamiento al uso real:** cada fruta se recorta de su fondo blanco y se coloca sobre un fondo
aleatorio (bandeja, mesa, cartón, con gradiente de luz, ruido, desenfoque leve y compresión JPEG). El
modelo aprende sobre la salida del **mismo** pipeline de segmentación que se usa en producción.

## 3. Modelo

63 características por imagen (histogramas de tono/saturación/valor, estadísticas Lab, forma —
aspecto, solidez, circularidad, extensión, excentricidad— y textura LBP + gradiente) →
estandarización → **regresión logística multinomial** con pesos balanceados por clase.

Comparación de familias de modelos (misma partición, mismas características):

| Modelo | F1 macro LOGO-CV (entrenamiento) | Exactitud prueba | F1 macro prueba | Sensibilidad papa (prueba) |
|---|---|---|---|---|
| **Regresión logística (C = 0.01)** | **0.586** | 0.710 | 0.680 | 0.24 |
| SVM RBF | 0.568 | 0.700 | 0.666 | 0.20 |
| Red neuronal (64 neuronas) | 0.520 | 0.707 | 0.677 | 0.24 |
| Red neuronal (32 neuronas) | 0.508 | 0.720 | 0.695 | 0.28 |
| Bosque aleatorio | 0.518 | 0.631 | 0.568 | 0.00 |
| Gradient boosting (histogramas) | 0.507 | 0.653 | 0.594 | 0.03 |

La selección se hizo por la validación cruzada (columna 2), no por la prueba. Ningún modelo no lineal
mejoró la validación por grupos; la diferencia en prueba con la red de 32 neuronas está dentro de la
variación esperable con tan pocos grupos. Se conservó el modelo más simple, interpretable y fácil de
exportar. Agregar características de brillo especular y textura a dos escalas tampoco cambió los
resultados de forma relevante (F1 LOGO-CV 0.56 → 0.59 con el modelo anterior a la corrección de la
segmentación).

## 4. Resultados en prueba (grupos nunca vistos)

| Métrica | Valor |
|---|---|
| Exactitud | **71 %** |
| F1 macro | 0.68 |
| ECE (calibración, 10 intervalos) | 0.055 |
| Brier multiclase | 0.39 |
| Exactitud cuando la probabilidad ≥ 60 % | 80 % (en el 76 % de las imágenes) |

| Clase | Sensibilidad | Precisión | Tasa de falsos positivos |
|---|---|---|---|
| Tomate | 91 % | 60 % | 20 % |
| Banano | 98 % | 98 % | 1 % |
| Papa | **24 %** | 70 % | 3 % |
| Otro | 72 % | 62 % | 15 % |

Matriz de confusión (filas = real, columnas = predicho):

| | tomate | banano | papa | otro |
|---|---|---|---|---|
| **tomate** | 272 | 6 | 0 | 22 |
| **banano** | 0 | 293 | 7 | 0 |
| **papa** | 119 | 0 | 71 | 110 |
| **otro** | 60 | 1 | 23 | 216 |

### Lectura honesta

- **Banano** se reconoce de forma fiable.
- **Tomate** se detecta bien, pero el modelo también llama «tomate» a otras frutas rojas y redondas
  (20 % de falsos positivos: manzana roja, durazno, papa roja).
- **Papa no es fiable.** Solo hay tres grabaciones de papa; la papa roja de prueba se parece más a un
  tomate o a «otro» que a las dos papas de entrenamiento. Con datos así no se puede afirmar que el
  modelo identifique papa.
- Por todo esto, en la aplicación **el producto declarado por el operador prevalece**. Una discrepancia
  con el modelo solo genera revisión humana (regla R02), y para clases con sensibilidad < 60 % se
  advierte en cada análisis (regla R04).
- Las probabilidades están razonablemente calibradas (ECE 0.055) **en este dominio**; no hay evidencia
  de que lo estén con fotos del mercado.

## 5. Detector de manchas: validación sintética

No hay un conjunto de datos con defectos reales etiquetados. Para medir al menos el algoritmo:
a imágenes limpias de los grupos de prueba se les pintan 1–3 manchas irregulares con un oscurecimiento
conocido (20–70 en la escala L de OpenCV; *leve* < 40 ≤ *marcada*). Los parámetros se eligieron con
imágenes de los grupos de entrenamiento (índice de Youden), y se reportan en prueba (150 imágenes por producto):

| Producto | Sensibilidad leve | Sensibilidad marcada | Falsos positivos en imágenes limpias | Precisión de regiones |
|---|---|---|---|---|
| Tomate | 50 % | 71 % | 16 % | 92 % |
| Banano | 71 % | 92 % | **53 %** | 79 % |
| Papa | 70 % | 92 % | 4 % | 97 % |

- El banano tiene muchos falsos positivos porque las puntas y manchas naturales de maduración son
  oscuras: el sistema lo advierte (regla R08).
- En tomate, el pedúnculo y los brillos explican parte de los falsos positivos.
- **Estas cifras no miden el desempeño con defectos reales** (golpes, hongos, pudrición): miden si el
  algoritmo encuentra zonas oscuras de tamaño y contraste conocidos. Validarlo requiere un conjunto
  etiquetado del mercado.

Durante el desarrollo se detectó y corrigió un error en la composición de imágenes (un relleno de
huecos fallaba cuando la fruta tocaba una esquina y pegaba un rectángulo blanco); todas las cifras
anteriores son posteriores a la corrección.

## 6. Validación de calidad de imagen

Nitidez = varianza del Laplaciano normalizada por el contraste, medida sobre el recorte del producto
(≤ 256 px). Umbrales elegidos con imágenes de prueba nítidas y desenfocadas artificialmente:

| Imágenes | Percentil 5 / 50 / 95 | Rechazadas como «desenfocada» (umbral 0.10) |
|---|---|---|
| Nítidas | 0.54 / 3.00 / 13.8 | 0 % |
| Desenfoque σ = 1.5 | 0.067 / 0.16 / 0.48 | 26 % (el resto, advertencia) |
| Desenfoque σ = 2.5 | 0.031 / 0.055 / 0.15 | 81 % |

## 7. Limitaciones del modelo

1. Dominio de laboratorio: una pieza aislada sobre fondo controlado. Con cajas llenas, varias piezas
   superpuestas o fondos del mismo color que el producto, la segmentación falla y la calidad lo marca.
2. Solo 3 clases de interés + «otro»; la papa no es fiable.
3. Las manchas se buscan solo en la cara visible y solo como zonas oscuras: no se detectan hongos
   blancos, ablandamiento, olor ni deterioro interno.
4. No hay evaluación con fotos de teléfono reales del mercado.
5. Nada en el sistema certifica inocuidad ni aptitud para consumo.

## 8. Cómo reproducir

```powershell
powershell -ExecutionPolicy Bypass -File scripts\train-model.ps1
```

Descarga ≈ 400 MB (solo las carpetas usadas), entrena (~1–2 min en CPU), sobrescribe
`backend/models/product_classifier_v1.json` y `metrics.json`, y vuelve a validar el detector.
Las semillas son fijas, pero pequeñas diferencias de versión de OpenCV/NumPy pueden mover las cifras
en décimas.
