# src/api/ — API REST (FastAPI)

Sirve los resultados del motor de riesgo al frontend e integra el asistente conversacional con IA.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `main.py` | Aplicación FastAPI con 9 endpoints + carga `.env` vía python-dotenv |

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/status` | Estado del pipeline y última actualización |
| GET | `/api/filters` | Cultivos y departamentos disponibles para filtros |
| GET | `/api/ranking` | Ranking paginado municipio–cultivo por IRA |
| GET | `/api/municipios` | GeoFeatureCollection con último IRA por municipio |
| GET | `/api/municipio/{codigo}` | Historial completo por municipio y cultivo |
| GET | `/api/municipio/{codigo}/deforestacion` | Datos de deforestación GFW/Hansen |
| GET | `/api/municipio/{codigo}/ndvi` | Serie temporal NDVI satelital (MODIS) |
| GET | `/api/municipio/{codigo}/multiagent` | Análisis multi-agente del riesgo |
| POST | `/api/municipio/{codigo}/chat` | Asistente IA: pregunta sobre el municipio (requiere OPENROUTER_API_KEY) |

## Dependencias externas

- `OPENROUTER_API_KEY` en `.env` para el endpoint `/chat` (modelo `openrouter/owl-alpha`)

## Desarrollo

```bash
make api
# o
uvicorn src.api.main:app --reload --port 8000
```
