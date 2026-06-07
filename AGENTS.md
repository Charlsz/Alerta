# AGENTS.md — Alerta: Plataforma de alerta temprana para riesgo climático agrícola

> Este archivo es la fuente de verdad para cualquier agente de IA o desarrollador que trabaje en este proyecto.
> Léelo completo antes de escribir o modificar cualquier archivo.

---

## 1. Qué es este proyecto

**Alerta** es una plataforma analítica y geoespacial para priorizar municipios y cultivos agrícolas en Colombia según su riesgo climático.

La salida principal es el **Índice de Riesgo Agroclimático (IRA)** por municipio × cultivo × periodo, visualizado en una plataforma web con mapa interactivo, ranking y fichas explicativas.

El concurso para el que se construye es **Datos al Ecosistema 2026 – IA para Colombia** (datos.gov.co). El reto asignado es: _"Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos"_.

**Deadline de publicación del producto:** 13 de julio de 2026.  
**Sustentaciones:** 14–17 de julio de 2026.

---

## 2. Reglas de oro para este proyecto

1. **Simple, directo, sencillo y bueno.** Nada de over-engineering. Si algo se puede hacer con una función de 20 líneas, no uses un patrón de 5 clases.
2. **Una sola responsabilidad por módulo.** Cada archivo/clase/función hace una cosa y la hace bien.
3. **Sin magia oculta.** Todo parámetro de configuración vive en `config.py` o en variables de entorno. Nada hardcodeado en la lógica.
4. **Reproducibilidad.** Cualquier resultado del IRA debe poder regenerarse corriendo `make pipeline`.
5. **Datos reales únicamente.** Nunca generes datos sintéticos para tests de integración. Usa fixtures pequeñas reales o marca el test como `@pytest.mark.skip`.
6. **Explica el riesgo.** Cada municipio que aparezca como "Alto" o "Crítico" debe poder justificar su score con importancias de variables (SHAP).
7. Evita hacer overengineering.
---

## 3. Arquitectura general

```
alerta/
├── data/                  # Datos locales (ignorados por git salvo muestras)
│   ├── raw/               # Datos descargados sin tocar
│   ├── processed/         # Tablas limpias y homologadas
│   └── features/          # Feature store final
├── src/
│   ├── ingestion/         # ETL por fuente (un archivo por fuente)
│   ├── features/          # Construcción de variables e índices
│   ├── risk/              # Cálculo del IRA y modelo de anomalías
│   ├── api/               # FastAPI – endpoints REST
│   └── web/               # React + Vite – frontend
├── tests/                 # Tests unitarios y de integración
├── notebooks/             # Exploración (no se importan en src/)
├── scripts/               # Scripts de CLI para correr el pipeline
├── Makefile               # Comandos principales
├── config.py              # Única fuente de configuración
├── requirements.txt
├── .env.example
└── AGENTS.md              # Este archivo
```

**Arquitectura del backend:** monolito modular. No microservicios. No hay razón para distribuir durante el concurso.

**Flujo de datos:**
```
Fuentes externas
     ↓
src/ingestion/  →  data/raw/
     ↓
src/features/   →  data/features/   (PostgreSQL + PostGIS)
     ↓
src/risk/       →  IRA por municipio × cultivo × periodo
     ↓
src/api/        →  FastAPI (JSON + GeoJSON)
     ↓
src/web/        →  React (mapa, ranking, fichas)
```

---

## 4. Módulo por módulo

### 4.1 `src/ingestion/`

**Regla:** un archivo Python por fuente de datos. Cada archivo expone una función principal `run(config) -> None` que descarga o lee el dato crudo y lo guarda en `data/raw/`.

| Archivo | Fuente | Salida |
|---|---|---|
| `eva.py` | EVA – datos.gov.co | `data/raw/eva.parquet` |
| `eva_calendario.py` | EVA Calendario | `data/raw/eva_calendario.parquet` |
| `ideam_precipitacion.py` | Precipitación IDEAM | `data/raw/ideam_precip.parquet` |
| `ideam_temperatura.py` | Temperatura Máxima IDEAM | `data/raw/ideam_tmax.parquet` |
| `ideam_estaciones.py` | Catálogo de estaciones IDEAM | `data/raw/ideam_estaciones.parquet` |
| `chirps.py` | CHIRPS (NetCDF/TIF) | `data/raw/chirps/` |
| `insumos.py` | Índice de insumos agrícolas UPRA | `data/raw/insumos.parquet` |
| `igac_municipios.py` | Shapefile IGAC municipios | `data/raw/municipios.gpkg` |

**Normas para ingestion:**
- Cada `run()` es idempotente: si el archivo ya existe y no es forzado, no vuelve a descargar.
- Los errores de descarga se loguean con `logging.warning`, no detienen el pipeline completo.
- Nada de lógica de negocio aquí. Solo descarga y persiste.

**APIs a usar:**
- datos.gov.co usa Socrata Open Data API (SODA). Endpoint base: `https://www.datos.gov.co/resource/{id}.json?$limit=50000&$offset=0`
- Para volúmenes grandes de IDEAM (precipitación: 280M filas, temperatura: 27M filas) usa descarga paginada con `$offset` o descarga por CSV/Export si la API lo soporta.

### 4.2 `src/features/`

**Regla:** una función por variable o grupo de variables. Las funciones reciben DataFrames y devuelven DataFrames. Sin efectos secundarios ocultos.

Estructura:
```
features/
├── clima.py        # Variables climáticas desde IDEAM y CHIRPS
├── produccion.py   # Variables EVA (área, rendimiento, estabilidad)
├── vulnerabilidad.py # Variables de insumos y DANE
├── spatial.py      # Joins espaciales estación→municipio, interpolación
└── store.py        # Escribe la tabla maestra a PostgreSQL/PostGIS
```

**Variables a construir (mínimo para IRA v1):**

*Sub-índice de Peligro Climático (SPC):*
- `precip_acum_7d` — Precipitación acumulada 7 días por municipio
- `precip_acum_30d` — Precipitación acumulada 30 días
- `precip_anomalia_30d` — Anomalía vs. media histórica CHIRPS (mismo periodo del año)
- `dias_secos_consecutivos` — Días sin lluvia antes del periodo
- `dias_lluvia_extrema` — Días con precipitación > percentil 95 histórico
- `tmax_media_7d` — Temperatura máxima media 7 días
- `tmax_anomalia_30d` — Anomalía de Tmax vs. histórico
- `dias_tmax_critica` — Días con Tmax > umbral por cultivo (ver `config.py`)

*Sub-índice de Exposición Productiva (SEP):*
- `area_sembrada` — Hectáreas sembradas cultivo × municipio (EVA)
- `area_cosechada`
- `rendimiento_promedio` — Media histórica rendimiento (ton/ha)
- `rendimiento_cv` — Coeficiente de variación del rendimiento (estabilidad)
- `participacion_municipal` — % del área nacional del cultivo en ese municipio
- `fase_fenologica` — 0/1 si el mes cae en periodo de siembra o cosecha (EVA Calendario)

*Sub-índice de Vulnerabilidad Económica (SVE):*
- `insumos_nivel` — Valor actual del índice de precios de insumos
- `insumos_anomalia_12m` — Anomalía vs. media 12 meses
- `insumos_delta_3m` — Cambio en los últimos 3 meses

**Normalización:** min-max entre 0 y 1 por variable, usando percentiles 1–99 para evitar que outliers extremos colapsen la escala.

### 4.3 `src/risk/`

```
risk/
├── ira.py          # Cálculo del IRA ponderado
├── anomaly.py      # Modelo IsolationForest o clustering
├── explainability.py # SHAP values por municipio
└── classify.py     # Asignar nivel Bajo/Medio/Alto/Crítico
```

**`ira.py`:** función `compute_ira(df, weights) -> DataFrame` que recibe la tabla de features normalizada y devuelve `ira_score` por fila.

```python
# Fórmula base
IRA = w1 * SPC + w2 * SEP + w3 * SVE
# Ponderaciones iniciales (ajustables en config.py)
# w1=0.5, w2=0.3, w3=0.2
```

**`anomaly.py`:** IsolationForest entrenado por cultivo (o por región si hay pocos municipios por cultivo). Genera `anomaly_score` y `is_anomaly` (bool). Se combina con IRA para la alerta final: un municipio puede tener IRA medio pero ser anómalo.

**`explainability.py`:** SHAP TreeExplainer o KernelExplainer (según el modelo). Genera `top3_variables` por municipio: las 3 variables que más contribuyen al score.

**`classify.py`:**
```python
def classify_ira(score: float) -> str:
    if score < 0.25: return "Bajo"
    if score < 0.50: return "Medio"
    if score < 0.75: return "Alto"
    return "Crítico"
```

### 4.4 `src/api/`

**Framework:** FastAPI. Un archivo por recurso.

```
api/
├── main.py         # App FastAPI, incluye todos los routers
├── deps.py         # Dependencias compartidas (DB session, etc.)
├── routers/
│   ├── map.py      # GET /map → GeoJSON municipios + IRA
│   ├── ranking.py  # GET /ranking?cultivo=&periodo=&top=20
│   ├── municipio.py # GET /municipio/{codigo}
│   └── features.py # GET /features/{codigo} (para revisión técnica)
└── schemas/
    ├── map.py
    ├── ranking.py
    └── municipio.py
```

**Normas para la API:**
- Paginación en todos los endpoints de lista (`limit`, `offset`).
- Respuestas en JSON estándar. El endpoint `/map` devuelve GeoJSON FeatureCollection.
- Sin lógica de negocio en los routers. Los routers llaman funciones de `src/risk/` o consultan la DB.
- CORS habilitado para desarrollo local.

**Endpoints mínimos:**

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/map` | GeoJSON con todos los municipios, IRA y nivel de riesgo |
| GET | `/ranking` | Top N municipios por IRA, filtrable por cultivo y periodo |
| GET | `/municipio/{codigo}` | Ficha completa: IRA, sub-índices, top3 variables, series históricas |
| GET | `/cultivos` | Lista de cultivos disponibles |
| GET | `/periodos` | Lista de periodos disponibles |
| GET | `/health` | Healthcheck (siempre devuelve 200) |

### 4.5 `src/web/`

**Stack:** React + Vite. Un componente por vista.

```
web/
├── src/
│   ├── components/
│   │   ├── Map.jsx          # Mapa Leaflet/MapLibre con municipios
│   │   ├── Ranking.jsx      # Tabla de ranking
│   │   ├── MunicipioCard.jsx # Ficha por municipio
│   │   ├── FilterBar.jsx    # Filtros (cultivo, periodo, departamento)
│   │   └── RiskBadge.jsx    # Badge de nivel (Bajo/Medio/Alto/Crítico)
│   ├── hooks/
│   │   └── useAPI.js        # Fetches a la API FastAPI
│   ├── App.jsx
│   └── main.jsx
├── index.html
└── vite.config.js
```

**Normas para el frontend:**
- La API URL viene de variable de entorno `VITE_API_URL`.
- El mapa usa GeoJSON del endpoint `/map`. No hardcodear geometrías.
- El color del municipio en el mapa mapea directamente al nivel IRA: verde (Bajo), amarillo (Medio), naranja (Alto), rojo (Crítico).
- Mostrar siempre las `top3_variables` en la ficha de municipio, con descripción legible (no nombre de columna crudo).

---

## 5. Base de datos

**Motor:** PostgreSQL 15 + PostGIS 3.

**Tablas principales:**

```sql
-- Geometría de municipios
municipios (
  codigo_municipio VARCHAR(6) PRIMARY KEY,
  nombre VARCHAR,
  departamento VARCHAR,
  geom GEOMETRY(MultiPolygon, 4326)
)

-- Feature store
features_municipio_cultivo (
  id SERIAL PRIMARY KEY,
  codigo_municipio VARCHAR(6),
  cultivo VARCHAR,
  periodo DATE,            -- primer día del periodo (mensual o semanal)
  -- variables SPC
  precip_acum_7d FLOAT,
  precip_acum_30d FLOAT,
  precip_anomalia_30d FLOAT,
  dias_secos_consecutivos INT,
  dias_lluvia_extrema INT,
  tmax_media_7d FLOAT,
  tmax_anomalia_30d FLOAT,
  dias_tmax_critica INT,
  -- variables SEP
  area_sembrada FLOAT,
  area_cosechada FLOAT,
  rendimiento_promedio FLOAT,
  rendimiento_cv FLOAT,
  participacion_municipal FLOAT,
  fase_fenologica INT,
  -- variables SVE
  insumos_nivel FLOAT,
  insumos_anomalia_12m FLOAT,
  insumos_delta_3m FLOAT
)

-- Resultados IRA
ira_resultados (
  id SERIAL PRIMARY KEY,
  codigo_municipio VARCHAR(6),
  cultivo VARCHAR,
  periodo DATE,
  spc FLOAT,
  sep FLOAT,
  sve FLOAT,
  ira_score FLOAT,
  ira_nivel VARCHAR(10),
  anomaly_score FLOAT,
  is_anomaly BOOLEAN,
  top3_variables JSONB,   -- [{"var": "precip_anomalia_30d", "shap": 0.23}, ...]
  calculado_en TIMESTAMP DEFAULT NOW()
)
```

**Índices obligatorios:**
```sql
CREATE INDEX ON features_municipio_cultivo (codigo_municipio, cultivo, periodo);
CREATE INDEX ON ira_resultados (cultivo, periodo, ira_nivel);
CREATE INDEX ON municipios USING GIST (geom);
```

---

## 6. Configuración central (`config.py`)

Todo parámetro ajustable vive aquí. Ningún número mágico en el código.

```python
# config.py
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class IRAConfig:
    # Ponderaciones de los sub-índices
    w_spc: float = 0.5
    w_sep: float = 0.3
    w_sve: float = 0.2

    # Umbrales de lluvia extrema (percentil histórico)
    precip_extrema_percentil: float = 95.0

    # Umbrales de temperatura crítica por cultivo (°C)
    tmax_critica_por_cultivo: Dict[str, float] = field(default_factory=lambda: {
        "maiz": 34.0,
        "arroz": 35.0,
        "papa": 28.0,
        "cafe": 30.0,
        "default": 33.0,
    })

    # Paginación SODA API
    soda_page_size: int = 50_000

    # Ruta de datos
    data_raw: str = "data/raw"
    data_processed: str = "data/processed"
    data_features: str = "data/features"

    # Clasificación IRA
    ira_niveles: Dict[str, tuple] = field(default_factory=lambda: {
        "Bajo":    (0.00, 0.25),
        "Medio":   (0.25, 0.50),
        "Alto":    (0.50, 0.75),
        "Crítico": (0.75, 1.00),
    })
```

Variables de entorno (`.env`, nunca en git):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/alerta
SODA_APP_TOKEN=...          # Token de app para datos.gov.co (opcional, aumenta rate limit)
VITE_API_URL=http://localhost:8000
```

---

## 7. Makefile (comandos principales)

```makefile
.PHONY: install db ingest features risk api web pipeline test

install:
	pip install -r requirements.txt
	cd src/web && npm install

db:
	psql -c "CREATE DATABASE alerta;" || true
	psql alerta -f scripts/schema.sql

ingest:
	python scripts/run_ingestion.py

features:
	python scripts/run_features.py

risk:
	python scripts/run_risk.py

pipeline: ingest features risk

api:
	uvicorn src.api.main:app --reload --port 8000

web:
	cd src/web && npm run dev

test:
	pytest tests/ -v
```

---

## 8. Tests

- **Tests unitarios** en `tests/unit/`: prueban funciones puras de `features/` y `risk/` con DataFrames de 10–50 filas construidos a mano.
- **Tests de integración** en `tests/integration/`: prueban que el pipeline end-to-end produce un `ira_resultados` no vacío con un subset pequeño de datos reales.
- **Tests de API** en `tests/api/`: prueban que los endpoints devuelven status 200 y el schema esperado.

Cobertura mínima objetivo: 70% en `src/risk/` y `src/features/`.

---

## 9. Datasets y sus URLs

| Tipo | Fuente | URL |
|---|---|---|
| Producción agro | EVA – datos.gov.co | https://www.datos.gov.co/resource/2pnw-mmge.json |
| Producción agro | Vista EVA | https://www.datos.gov.co/resource/fp29-z39g.json |
| Calendario cultivos | EVA Calendario 2023–2024 | https://www.datos.gov.co/resource/4229-puwp.json |
| Clima observado | Precipitación IDEAM | https://www.datos.gov.co/resource/s54a-sgyg.json |
| Clima observado | Temperatura Máxima IDEAM | https://www.datos.gov.co/resource/ccvq-rp9s.json |
| Clima observado | Dirección del Viento IDEAM | https://www.datos.gov.co/resource/kiw7-v9ta.json |
| Estaciones | Catálogo Estaciones IDEAM | https://www.datos.gov.co/resource/hp9r-jxuu.json |
| Insumos | Índice Precios Insumos Agrícolas | https://www.datos.gov.co/resource/gwbi-fnzs.json |
| Clima histórico | CHIRPS | https://www.chc.ucsb.edu/data/chirps |
| Satelital | Sentinel-1 SAR | https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar |
| Territorio | Colombia en Mapas | https://www.colombiaenmapas.gov.co |
| Cartografía | IGAC Datos Abiertos | https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia |
| Metodología | Alliance Bioversity–CIAT | https://alliancebioversityciat.org/es |

**Nota sobre volúmenes IDEAM:**  
- Precipitación: ~280M filas → paginar con `$offset`, filtrar por fecha y departamento desde el inicio.  
- Temperatura Máxima: ~27M filas → misma estrategia.  
- Nunca descargar todo el dataset en memoria de una sola vez.

---

## 10. Convenciones de código

- **Nombres de variables:** `snake_case` en Python, `camelCase` en JavaScript/JSX.
- **Nombres de columnas en DB y DataFrames:** `snake_case` siempre. Sin tildes ni espacios.
- **Código en español o inglés:** inglés para código y comentarios técnicos; español para strings de UI y documentación de usuario.
- **Logging:** usar `logging` estándar de Python. Nada de `print()` en producción.
- **Type hints:** obligatorios en todas las funciones de `src/`.
- **Docstrings:** una línea describiendo qué hace la función. No sobre-documentar.
- **Sin dependencias circulares:** `ingestion` no importa de `features`; `features` no importa de `risk`; `risk` no importa de `api`.

---

## 11. Lo que NO se debe hacer

- **No usar Jupyter notebooks dentro de `src/`.** Los notebooks son solo para exploración en `notebooks/`.
- **No hardcodear rutas absolutas.** Todo relativo a la raíz del proyecto o via `config.py`.
- **No entrenar modelos en los endpoints de la API.** Los modelos se entrenan en el pipeline y se serializan (joblib). La API solo carga y usa.
- **No usar `SELECT *` en queries SQL.** Seleccionar solo las columnas necesarias.
- **No romper el contrato de la API** sin actualizar los schemas en `src/api/schemas/`.
- **No mezclar lógica de ingesta con lógica de features.** Son capas distintas.

---

## 12. Estado actual y próximos pasos

> Actualizar esta sección conforme avance el proyecto.

**Completado:**
- [ ] Diseño de arquitectura y AGENTS.md

**En progreso:**
- [ ] Scripts de ingesta: EVA, Precipitación IDEAM, Temperatura IDEAM, Estaciones IDEAM, Insumos

**Pendiente:**
- [ ] Feature engineering (clima.py, produccion.py, vulnerabilidad.py, spatial.py)
- [ ] Cálculo IRA v1
- [ ] Modelo de anomalías IsolationForest
- [ ] SHAP explicabilidad
- [ ] API FastAPI (endpoints básicos)
- [ ] Frontend React (mapa + ranking + ficha)
- [ ] Publicación en datos.gov.co (deadline: 13 julio 2026)
- [ ] Sustentación virtual (14–17 julio 2026)

---

*Última actualización: junio 2026*
