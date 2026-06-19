# AGENTS.md — Alerta: Plataforma de alerta temprana para riesgo climático agrícola

> **Fuente de verdad del proyecto.** Cualquier agente de IA o desarrollador debe leer este archivo completo antes de escribir o modificar cualquier código.

---

## 1. Qué es este proyecto

**Alerta** es una plataforma analítica y geoespacial para priorizar municipios y cultivos agrícolas en Colombia según su riesgo climático.

La salida principal es el **Índice de Riesgo Agroclimático (IRA)** por municipio × cultivo × periodo, visualizado en una plataforma web con mapa interactivo, ranking y fichas explicativas.

El concurso es **Datos al Ecosistema 2026 – IA para Colombia** (datos.gov.co).  
Reto asignado: _"Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos"_.

| Hito | Fecha |
|---|---|
| Publicación del producto en datos.gov.co | 13 julio 2026 |
| Sustentaciones virtuales | 14–17 julio 2026 |

---

## 2. Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| Lenguaje | Python 3.12 | ETL, features, IA, API |
| Motor de datos | **DuckDB** | Analítica local embebida, lee Parquet directamente, sin servidor |
| Almacenamiento | Parquet + `data/alerta.duckdb` | Simple, portable, reproducible |
| Geoespacial | GeoPandas + Shapely | Joins espaciales y manejo de geometrías |
| IA / ML | scikit-learn + SHAP | Detección de anomalías, explicabilidad |
| API | FastAPI | REST rápido, tipado, documentación automática |
| Frontend | **Next.js** (App Router) + TypeScript | Enrutamiento, SSR, componentes |
| Mapas | Leaflet (react-leaflet) | Mapas interactivos en el frontend |
| Entorno | **Docker + Docker Compose** | Reproducibilidad total entre equipos |

> **Nota:** No se usa PostgreSQL ni PostGIS. DuckDB cumple el mismo rol para este proyecto sin necesitar un servidor.

---

## 3. Reglas de oro

1. **Simple, directo, sencillo y bueno.** Si algo se resuelve en 20 líneas, no uses 5 clases.
2. **Una responsabilidad por módulo.** Cada archivo hace una cosa y la hace bien.
3. **Sin magia oculta.** Todo parámetro vive en `config.py` o en variables de entorno. Nada hardcodeado.
4. **Reproducibilidad.** Cualquier resultado del IRA se regenera con `make pipeline`.
5. **Datos reales únicamente.** Nunca generes datos sintéticos en tests de integración.
6. **Explica el riesgo.** Todo municipio "Alto" o "Crítico" justifica su score con SHAP.
7. **Sin over-engineering.** Monolito modular, no microservicios.

---

## 4. Arquitectura general

```
alerta/
├── data/                    # Datos locales — ignorados por git salvo muestras
│   ├── raw/                 # Datos descargados sin modificar
│   ├── processed/           # Tablas limpias y homologadas
│   ├── features/            # Feature store (Parquet)
│   └── alerta.duckdb        # Base de datos analítica local
├── src/
│   ├── ingestion/           # ETL por fuente (un archivo = una fuente)
│   ├── features/            # Construcción de variables e índices
│   ├── risk/                # Cálculo del IRA y modelo de anomalías
│   ├── api/                 # FastAPI — endpoints REST
│   └── web/                 # Next.js — frontend
├── tests/
│   ├── unit/
│   └── integration/
├── notebooks/               # Solo exploración — nunca importar desde src/
├── scripts/                 # CLI: run_ingestion.py, run_features.py, run_risk.py
├── Makefile
├── config.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── AGENTS.md
```

**Flujo de datos:**
```
Fuentes externas (SODA API / archivos)
        ↓
src/ingestion/   →  data/raw/*.parquet
        ↓
src/features/    →  data/alerta.duckdb  (tablas: features_municipio_cultivo)
        ↓
src/risk/        →  data/alerta.duckdb  (tabla: ira_resultados)
        ↓
src/api/         →  FastAPI JSON + GeoJSON
        ↓
src/web/         →  Next.js (mapa, ranking, fichas)
```

---

## 5. Módulo por módulo

### 5.1 `src/ingestion/`

Un archivo Python por fuente. Cada archivo expone `run(config) -> None`.

| Archivo | Fuente | Salida en `data/raw/` |
|---|---|---|
| `eva.py` | EVA – datos.gov.co | `eva.parquet` |
| `eva_calendario.py` | EVA Calendario | `eva_calendario.parquet` |
| `ideam_estaciones.py` | Catálogo estaciones IDEAM | `ideam_estaciones.parquet` |
| `ideam_precipitacion.py` | Precipitación IDEAM | `ideam_precip.parquet` |
| `ideam_temperatura.py` | Temperatura Máxima IDEAM | `ideam_tmax.parquet` |
| `insumos.py` | Índice precios insumos UPRA | `insumos.parquet` |
| `igac_municipios.py` | Shapefile IGAC municipios | `municipios.gpkg` |
| `chirps.py` | CHIRPS precipitación histórica | `chirps/` (archivos NetCDF) |

**Normas:**
- `run()` es idempotente: si el archivo ya existe, no descarga de nuevo (salvo `--force`).
- Errores → `logging.warning`. No detienen el pipeline.
- Sin lógica de negocio. Solo descarga y persiste.
- La API SODA usa: `https://www.datos.gov.co/resource/{id}.json?$limit=50000&$offset=0`
- Para IDEAM (volúmenes grandes) filtrar por fecha: `$where=fechaobservacion >= '2020-01-01'`

### 5.2 `src/features/`

Funciones puras: reciben DataFrames o conexión DuckDB, devuelven DataFrames.

| Archivo | Responsabilidad |
|---|---|
| `spatial.py` | Join estación IDEAM → municipio (lat/lon → código DANE) |
| `produccion.py` | Variables EVA: área, rendimiento, estabilidad, participación |
| `clima.py` | Variables climáticas: anomalías, días secos, días extremos |
| `vulnerabilidad.py` | Variables de insumos: nivel, anomalía 12m, delta 3m |
| `store.py` | Join de sub-índices → tabla maestra en DuckDB |

**Variables mínimas para IRA v1:**

*SPC — Peligro Climático:*
- `precip_acum_7d`, `precip_acum_30d`
- `precip_anomalia_30d` (vs. histórico CHIRPS)
- `dias_secos_consecutivos`, `dias_lluvia_extrema`
- `tmax_media_7d`, `tmax_anomalia_30d`, `dias_tmax_critica`

*SEP — Exposición Productiva:*
- `area_sembrada`, `area_cosechada`
- `rendimiento_promedio`, `rendimiento_cv`
- `participacion_municipal`, `fase_fenologica`

*SVE — Vulnerabilidad Económica:*
- `insumos_nivel`, `insumos_anomalia_12m`, `insumos_delta_3m`

**Normalización:** min-max entre 0 y 1, usando percentiles p1–p99 para robustecer ante outliers.

### 5.3 `src/risk/`

| Archivo | Responsabilidad |
|---|---|
| `ira.py` | Calcula SPC, SEP, SVE e IRA ponderado |
| `anomaly.py` | IsolationForest por cultivo → `anomaly_score`, `is_anomaly` |
| `explainability.py` | SHAP top-3 variables por municipio |
| `classify.py` | Asigna nivel Bajo / Medio / Alto / Crítico |

**Fórmula IRA:**
```
IRA = w_spc × SPC + w_sep × SEP + w_sve × SVE
```
Ponderaciones iniciales en `config.py`: w_spc=0.5, w_sep=0.3, w_sve=0.2.

**Modelos entrenados** se serializan con `joblib` en `data/models/`. La API solo carga y usa — nunca entrena.

### 5.4 `src/api/`

FastAPI. Un archivo por recurso. Sin lógica de negocio en los routers.

```
api/
├── main.py          # App + CORS + routers
├── deps.py          # Dependencias compartidas (conexión DuckDB)
├── routers/
│   ├── map.py       # GET /map → GeoJSON
│   ├── ranking.py   # GET /ranking
│   ├── municipio.py # GET /municipio/{codigo}
│   └── health.py    # GET /health
└── schemas/         # Pydantic schemas por recurso
```

| Endpoint | Descripción |
|---|---|
| `GET /health` | Healthcheck |
| `GET /cultivos` | Lista de cultivos disponibles |
| `GET /periodos` | Lista de periodos disponibles |
| `GET /map?cultivo=&periodo=` | GeoJSON municipios + IRA |
| `GET /ranking?cultivo=&periodo=&top=20` | Top N municipios por riesgo |
| `GET /municipio/{codigo}?cultivo=&periodo=` | Ficha completa con SHAP |

**CORS** habilitado para `http://localhost:3000` en desarrollo.

### 5.5 `src/web/`

Next.js + App Router + TypeScript. Un componente por responsabilidad.

```
web/
├── app/
│   ├── page.tsx              # Vista principal
│   └── municipio/[codigo]/
│       └── page.tsx          # Ficha por municipio (ruta dinámica)
├── components/
│   ├── Map.tsx               # Mapa Leaflet — solo Client Component
│   ├── Ranking.tsx           # Tabla de ranking
│   ├── MunicipioCard.tsx     # Ficha resumen
│   ├── FilterBar.tsx         # Selectores cultivo / periodo
│   └── RiskBadge.tsx         # Badge de color por nivel
├── lib/
│   └── api.ts                # Fetch centralizado a FastAPI
└── Dockerfile                # Imagen Next.js para Docker Compose
```

**Normas frontend:**
- `NEXT_PUBLIC_API_URL` desde variables de entorno. Sin URLs hardcodeadas.
- Leaflet requiere `'use client'` — SSR no funciona con `window`.
- Colores IRA: verde (Bajo), amarillo (Medio), naranja (Alto), rojo (Crítico).
- Mostrar siempre `top3_variables` con etiqueta en español, no el nombre de columna crudo.

---

## 6. DuckDB como motor de datos

DuckDB se usa como base de datos analítica local embebida. No requiere servidor.

**Conexión desde Python:**
```python
import duckdb
from config import config

con = duckdb.connect(config.duckdb_path)
```

**Extensión espacial** (para geometrías):
```sql
INSTALL spatial;
LOAD spatial;
```

**Tablas principales en `alerta.duckdb`:**

```sql
-- Estaciones climáticas con geometría
estaciones (
  codigo_estacion VARCHAR PRIMARY KEY,
  nombre          VARCHAR,
  municipio       VARCHAR,
  codigo_municipio VARCHAR,
  departamento    VARCHAR,
  latitud         DOUBLE,
  longitud        DOUBLE
)

-- Feature store: una fila por municipio × cultivo × periodo
features_municipio_cultivo (
  codigo_municipio  VARCHAR,
  cultivo           VARCHAR,
  periodo           DATE,
  -- SPC
  precip_acum_7d           DOUBLE,
  precip_acum_30d          DOUBLE,
  precip_anomalia_30d      DOUBLE,
  dias_secos_consecutivos  INTEGER,
  dias_lluvia_extrema      INTEGER,
  tmax_media_7d            DOUBLE,
  tmax_anomalia_30d        DOUBLE,
  dias_tmax_critica        INTEGER,
  -- SEP
  area_sembrada            DOUBLE,
  area_cosechada           DOUBLE,
  rendimiento_promedio     DOUBLE,
  rendimiento_cv           DOUBLE,
  participacion_municipal  DOUBLE,
  fase_fenologica          INTEGER,
  -- SVE
  insumos_nivel            DOUBLE,
  insumos_anomalia_12m     DOUBLE,
  insumos_delta_3m         DOUBLE,
  PRIMARY KEY (codigo_municipio, cultivo, periodo)
)

-- Resultados IRA
ira_resultados (
  codigo_municipio  VARCHAR,
  cultivo           VARCHAR,
  periodo           DATE,
  spc               DOUBLE,
  sep               DOUBLE,
  sve               DOUBLE,
  ira_score         DOUBLE,
  ira_nivel         VARCHAR,
  anomaly_score     DOUBLE,
  is_anomaly        BOOLEAN,
  top3_variables    JSON,     -- [{"var": "precip_anomalia_30d", "shap": 0.23}]
  calculado_en      TIMESTAMP DEFAULT current_timestamp,
  PRIMARY KEY (codigo_municipio, cultivo, periodo)
)
```

---

## 7. Configuración central (`config.py`)

Toda constante ajustable vive en `IRAConfig`. Ver el archivo `config.py` en la raíz.

**Variables de entorno (`.env`):**
```
SODA_APP_TOKEN=          # Token opcional para datos.gov.co
DUCKDB_PATH=             # Ruta del archivo DuckDB (opcional, hay default)
API_PORT=8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 8. Makefile — comandos disponibles

| Comando | Acción |
|---|---|
| `make help` | Lista todos los comandos |
| `make install` | Instala dependencias Python y Node |
| `make up` | Levanta backend + frontend con Docker Compose |
| `make down` | Detiene los contenedores |
| `make ingest` | Descarga datos crudos |
| `make features` | Construye variables en DuckDB |
| `make risk` | Calcula IRA + anomalías + SHAP |
| `make pipeline` | Corre ingest + features + risk |
| `make api` | Inicia FastAPI en modo desarrollo |
| `make web` | Inicia Next.js en modo desarrollo |
| `make test` | Corre tests con pytest + coverage |
| `make lint` | Verifica estilo con ruff |

---

## 9. Tests

- `tests/unit/` — funciones puras con DataFrames pequeños construidos a mano.
- `tests/integration/` — pipeline end-to-end con subset real de datos.
- Cobertura mínima objetivo: **70%** en `src/risk/` y `src/features/`.

---

## 10. Datasets y URLs

| Tipo | Fuente | Resource ID / URL |
|---|---|---|
| Producción agro | EVA | `2pnw-mmge` |
| Producción agro | Vista EVA | `fp29-z39g` |
| Calendario cultivos | EVA Calendario | `4229-puwp` |
| Clima observado | Precipitación IDEAM | `s54a-sgyg` |
| Clima observado | Temperatura Máxima IDEAM | `ccvq-rp9s` |
| Estaciones | Catálogo Estaciones IDEAM | `hp9r-jxuu` |
| Insumos | Índice Precios Insumos UPRA | `gwbi-fnzs` |
| Clima histórico | CHIRPS | https://www.chc.ucsb.edu/data/chirps |
| Cartografía | IGAC Datos Abiertos | https://geoportal.igac.gov.co |

Endpoint base SODA: `https://www.datos.gov.co/resource/{id}.json`

**Volúmenes IDEAM — estrategia obligatoria:**
- Precipitación (~280M filas): filtrar `$where=fechaobservacion >= '2020-01-01'` + paginación.
- Temperatura (~27M filas): misma estrategia.
- Nunca cargar el dataset completo en memoria.

---

## 11. Convenciones de código

- `snake_case` en Python; `camelCase` en TypeScript.
- Nombres de columnas en DuckDB: `snake_case`, sin tildes, sin espacios.
- Inglés para código y comentarios técnicos; español para strings de UI.
- `logging` estándar, nunca `print()` en producción.
- Type hints obligatorios en todas las funciones de `src/`.
- Sin dependencias circulares entre capas: `ingestion` → `features` → `risk` → `api`.

---

## 12. Lo que NO se debe hacer

- No usar notebooks dentro de `src/`.
- No hardcodear rutas absolutas.
- No entrenar modelos en endpoints de la API.
- No usar `SELECT *` en queries SQL.
- No romper el contrato de la API sin actualizar los schemas.
- No mezclar lógica de ingesta con lógica de features.
- No instalar PostgreSQL ni psycopg2 — este proyecto usa DuckDB.

---

## 13. Estado del proyecto

**Completado (Paso 0):**
- [x] Stack definido: Python + DuckDB + Docker + FastAPI + Next.js
- [x] `requirements.txt` — sin PostgreSQL, con DuckDB
- [x] `config.py` — con `duckdb_path`
- [x] `Makefile` — sin `make db`, con `make up/down/lint`
- [x] `.env.example` — sin `DATABASE_URL`, con `NEXT_PUBLIC_API_URL`
- [x] `Dockerfile` — imagen Python 3.12 slim
- [x] `docker-compose.yml` — backend + frontend
- [x] `AGENTS.md` — actualizado al stack real

**Paso 1 — En progreso:**
- [ ] Verificar scripts de ingesta existentes (eva, estaciones, precipitación, temperatura, insumos)
- [ ] Completar `igac_municipios.py` (vacío)
- [ ] Completar `chirps.py` (vacío)
- [ ] Crear `scripts/run_ingestion.py`

**Paso 2 — Pendiente:**
- [ ] Cargar Parquet a DuckDB (crear tablas)
- [ ] Limpieza y homologación (tipos, municipios, joins espaciales)

**Paso 3 — Pendiente:**
- [ ] Features: spatial.py, produccion.py, clima.py, vulnerabilidad.py, store.py

**Paso 4 — Pendiente:**
- [ ] IRA: ira.py, anomaly.py, explainability.py, classify.py

**Paso 5 — Pendiente:**
- [ ] API FastAPI (endpoints)
- [ ] Frontend Next.js (mapa + ranking + ficha)
- [ ] Publicación en datos.gov.co (13 julio 2026)
- [ ] Sustentación virtual (14–17 julio 2026)

---

*Última actualización: junio 2026 — Paso 0 completado*
