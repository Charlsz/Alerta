# src/risk/ — Motor de riesgo agroclimático

Calcula el Índice de Riesgo Agroclimático (IRA), detecta anomalías y genera predicciones de rendimiento.
Lee de la tabla `features_municipio_cultivo` y escribe resultados en DuckDB.

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `ira.py` | 35 | Calcula IRA ponderado (SPC + SEP + SVE) y asigna nivel de riesgo |
| `classify.py` | 9 | Clasifica score IRA en Bajo / Medio / Alto / Crítico |
| `anomaly.py` | 81 | Detección de anomalías multivariadas con IsolationForest |
| `predict_rendimiento.py` | 236 | Modelo predictivo de rendimiento (XGBoost/RF) con SHAP y CV |
| `explainability.py` | 78 | Explicabilidad SHAP del score IRA por fila |
