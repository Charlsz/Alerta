# src/ — Código fuente

| Carpeta | Propósito |
|---------|-----------|
| `api/` | API REST FastAPI — 4 endpoints: filters, ranking, municipios (GeoJSON), municipio detalle |
| `features/` | Feature engineering: construye variables e indicadores en DuckDB |
| `ingestion/` | Descarga datos crudos desde fuentes externas a `data/raw/` |
| `risk/` | Motor de riesgo: IRA, anomalías, predicción de rendimiento |
| `web/` | Frontend Next.js 15 — mapa Leaflet, ranking, ficha municipio |

## Flujo del pipeline

```
ingestion/  →  data/raw/*.parquet  →  features/  →  DuckDB  →  risk/  →  resultados
```

Cada capa se comunica a través de tablas en DuckDB (`data/alerta.duckdb`).
Los orquestadores están en `scripts/`.
