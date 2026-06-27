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
estaciones → municipios → eva → eva_calendario → insumos → dane → dane_nbi → precipitacion → temperatura → humedad → presion → tambiente → viento → ndvi

### `features` — Carga a DuckDB, limpia, construye variables, tabla maestra
load_duckdb → clean → spatial → produccion → clima → vulnerabilidad → store

### `risk` — Calcula IRA, anomalías, predicciones de rendimiento
predict → nnet → anomaly → ira → store_risk

## Automatización

El pipeline puede ejecutarse automáticamente cada semana mediante GitHub Actions:
`.github/workflows/pipeline.yml` (cron: lunes 5AM). También soporta `workflow_dispatch`
para ejecución manual desde la interfaz de GitHub.
