# scripts/ — Orquestadores del pipeline

Scripts ejecutables que corren las etapas del pipeline en orden.
Todos aceptan `--force` para re-ejecutar y `--only PASO` para correr un paso específico.

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `run_ingestion.py` | 89 | Descarga datos crudos de todas las fuentes externas a `data/raw/` |
| `run_features.py` | 79 | Carga Parquets a DuckDB, limpia, construye variables y tabla maestra |
| `run_risk.py` | 70 | Calcula IRA, anomalías y predicciones de rendimiento |
| `schema.sql` | 275 | Esquema de referencia del DuckDB (no se ejecuta, solo documentación) |

## Uso

```bash
# Pipeline completo
python scripts/run_ingestion.py
python scripts/run_features.py
python scripts/run_risk.py

# Re-ejecutar todo forzando re-descarga
python scripts/run_ingestion.py --force

# Correr un solo paso
python scripts/run_features.py --only clima
python scripts/run_risk.py --only ira

# Pipeline end-to-end (vía Makefile)
make pipeline
```
