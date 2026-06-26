# scripts/ — Orquestador del pipeline

Un único script `run.py` que corre cualquier etapa del pipeline.

## Uso

```bash
# Pipeline completo por etapa
python scripts/run.py ingest
python scripts/run.py features
python scripts/run.py risk

# Re-ejecutar forzando
python scripts/run.py ingest --force

# Correr un solo paso
python scripts/run.py features --only clima
python scripts/run.py risk --only ira

# Pipeline end-to-end
make pipeline
```

## Etapas y pasos

### `ingest` — Descarga datos crudos de fuentes externas a `data/raw/`
estaciones → municipios → eva → eva_calendario → insumos → dane → precipitacion → temperatura → humedad → presion → tambiente → chirps

### `features` — Carga a DuckDB, limpia, construye variables, tabla maestra
load_duckdb → clean → spatial → produccion → clima → vulnerabilidad → store

### `risk` — Calcula IRA, anomalías, predicciones de rendimiento
predict → anomaly → ira → store_risk
