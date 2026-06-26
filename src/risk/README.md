# src/risk/ — Motor de riesgo agroclimático

Calcula el Índice de Riesgo Agroclimático (IRA), detecta anomalías y genera predicciones de rendimiento.
Lee de la tabla `features_municipio_cultivo` y escribe resultados en DuckDB.

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `ira.py` | 85 | Calcula IRA ponderado (SPC + SEP + SVE) y asigna nivel de riesgo |
| `classify.py` | 12 | Clasifica score IRA en Bajo / Medio / Alto / Crítico |
| `anomaly.py` | 137 | Detección de anomalías multivariadas con IsolationForest |
| `predict_rendimiento.py` | 285 | Modelo predictivo de rendimiento (RandomForest) con SHAP y CV |
| `store_risk.py` | 67 | Une ira_scores + anomaly_scores + predicciones_rendimiento en `ira_resultados` |
| `explainability.py` | 100 | Explicabilidad SHAP del score IRA por fila |
