# src/ — Código fuente

| Carpeta | Propósito |
|---------|-----------|
| `api/` | API REST FastAPI (en construcción — archivos vacíos) |
| `features/` | Feature engineering: construye variables e indicadores en DuckDB |
| `ingestion/` | Descarga datos crudos desde fuentes externas a `data/raw/` |
| `risk/` | Motor de riesgo: IRA, anomalías, predicción de rendimiento |
| `web/` | Frontend React + Vite (en construcción — archivos vacíos) |

## Flujo del pipeline

```
ingestion/  →  data/raw/*.parquet  →  features/  →  DuckDB  →  risk/  →  resultados
```

Cada capa se comunica a través de tablas en DuckDB (`data/alerta.duckdb`).
Los orquestadores están en `scripts/`.
