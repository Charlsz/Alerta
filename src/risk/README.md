# src/risk/ — Motor de riesgo agroclimático

Calcula el Índice de Riesgo Agroclimático (IRA), detecta anomalías y genera predicciones de rendimiento.
Lee de la tabla `features_municipio_cultivo` y escribe resultados en DuckDB.

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `ira.py` | 89 | Calcula IRA ponderado (SPC + SEP + SVE) y asigna nivel de riesgo |
| `anomaly.py` | 137 | Detección de anomalías multivariadas con IsolationForest |
| `predict_rendimiento.py` | 285 | Modelo predictivo de rendimiento (RandomForest/XGBoost) con SHAP y CV |
| `nnet_rendimiento.py` | 102 | Red neuronal (MLPRegressor, 2 capas ocultas) para predicción de rendimiento |
| `multi_agent.py` | 90 | Sistema multi-agente: 3 agentes (Clima, Producción, Vulnerabilidad) + Coordinador |
| `store_risk.py` | 67 | Une ira_scores + anomaly_scores + predicciones en `ira_resultados` |
| `explainability.py` | 100 | Explicabilidad SHAP del score IRA por fila |
