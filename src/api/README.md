# src/api/ — API REST (FastAPI)

Sirve los resultados del motor de riesgo al frontend.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `main.py` | Aplicación FastAPI con 4 endpoints: filters, ranking, municipios (GeoJSON), municipio detalle |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/filters` | Cultivos y departamentos disponibles para filtros |
| GET | `/api/ranking` | Ranking paginado municipio–cultivo por IRA |
| GET | `/api/municipios` | GeoFeatureCollection con último IRA por municipio |
| GET | `/api/municipio/{codigo}` | Historial completo por municipio y cultivo |

## Desarrollo

```bash
make api
# o
uvicorn src.api.main:app --reload --port 8000
```
