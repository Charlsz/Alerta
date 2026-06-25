# src/api/ — API REST (FastAPI)

En construcción. Archivos creados como scaffolding inicial, todos vacíos.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `main.py` | Punto de entrada de la aplicación FastAPI |
| `deps.py` | Dependencias compartidas (inyección de conexión DuckDB, etc.) |
| `routers/ranking.py` | Endpoints de ranking municipio–cultivo por IRA |
| `routers/municipio.py` | Endpoints de ficha detallada por municipio |
| `routers/map.py` | Endpoints de datos geoespaciales para el mapa |
| `routers/features.py` | Endpoints de acceso a features individuales |
| `schemas/ranking.py` | Modelos Pydantic para respuestas de ranking |
| `schemas/municipio.py` | Modelos Pydantic para ficha de municipio |
| `schemas/map.py` | Modelos Pydantic para datos del mapa |
