"""Módulo de visión artificial de MercaCircular.

Componentes (todos implementados con OpenCV + NumPy, sin servicios externos):

- ``quality``       validación de la imagen (resolución, nitidez, exposición, cobertura).
- ``segmentation``  separación producto / fondo a partir del color del borde.
- ``features``      vector de 63 características de color, forma y textura.
- ``classifier``    regresión logística multinomial exportada a JSON (inferencia en NumPy).
- ``anomalies``     detector heurístico de manchas oscuras (indicios de deterioro).
- ``pipeline``      orquesta todo y produce un resultado auditable.

El entrenamiento vive en ``backend/ml`` y está separado de la inferencia.
"""
