# src/ingestion/

Descarga los datos crudos de cada fuente externa y los guarda en `data/raw/`.
Cada script es independiente, idempotente y expone `run(force=False)` para el orquestador (`scripts/run_ingestion.py`).

---

## Archivo por archivo

### `_soda.py` — Cliente SODA paginado

**Qué hace:** Cliente reutilizable para la API de `datos.gov.co`. La función `fetch_soda()` descarga datasets públicos del gobierno colombiano con paginación automática vía `$offset`/`$limit`.

**Cómo lo hace:** Construye URLs secuenciales (`?$limit=50000&$offset=0`, luego `$offset=50000`, etc.), descarga páginas JSON hasta recibir una vacía. Soporta `$where` para filtrar por fecha y `$order` para orden determinista.

**Por qué así:** SODA es la API oficial de datos abiertos Colombia. La paginación es necesaria porque los datasets tienen decenas de millones de filas y SODA no permite descargas completas sin paginar. Se usa JSON en vez de CSV aquí porque `_soda.py` es el módulo original; los scripts más nuevos (`ideam_precipitacion.py`, `ideam_temperatura.py`, `eva_calendario.py`) migraron a CSV/Excel directo por simplicidad.

---

### `igac_municipios.py` — Geometría oficial de municipios

**Qué hace:** Descarga la capa de polígonos municipales de Colombia con código DANE de 5 dígitos, nombre del municipio, departamento y geometría. Guarda como GeoPackage en `data/raw/municipios.gpkg`. Es el join base de todo el sistema — sin él, las estaciones IDEAM no tienen código municipal asignado.

**Cómo lo hace:** Intenta primero el FeatureServer REST del DANE (MGN 2022). Si falla (timeout), cae a un GeoJSON en GitHub (`caticoa3/colombia_mapa`). Renombra columnas al esquema estándar del proyecto (codigo_municipio, nombre_municipio, etc.) y asegura CRS EPSG:4326.

**Por qué así:** La fuente primaria (DANE) es la oficial, pero su servidor geográfico tiene disponibilidad irregular. El fallback en GitHub es un dataset MGN 2018 simplificado con los mismos campos base. Se usa GeoPackage porque preserve geometrías y es portátil. No se usa SQLite directo porque geopandas maneja la proyección y el renombre de columnas de forma más expresiva.

---

### `ideam_estaciones.py` — Catálogo de estaciones IDEAM

**Qué hace:** Descarga el catálogo de estaciones meteorológicas del IDEAM (~9,600 estaciones) con nombre, código, latitud, longitud, departamento, municipio y tipo. Guarda en `data/raw/ideam_estaciones.parquet`.

**Cómo lo hace:** Usa `_soda.fetch_soda()` con el dataset ID `hp9r-jxuu`. Es un dataset pequeño (~10K filas), una sola página SODA.

**Por qué así:** Es el dataset más chico del pipeline (~1 MB), no justifica una optimización de descarga. El catálogo se necesita temprano para el join espacial con municipios.

---

### `ideam_precipitacion.py` — Precipitación IDEAM

**Qué hace:** Descarga observaciones diarias de precipitación del IDEAM (~280M filas total histórico). Filtra por los últimos 5 años para evitar el volumen completo. Guarda en `data/raw/ideam_precip.parquet`.

**Cómo lo hace:** Descarga CSV directo desde la URL SODA (`/resource/s54a-sgyg.csv`) con `$where=fechaobservacion >= 'YYYY-MM-DD'` y `$limit=5000000`. Usa `pd.read_csv()` con `low_memory=False` para evitar warnings de tipos mixtos.

**Por qué así:** Originalmente usaba paginación SODA JSON como los demás, pero la paginación de ~280M filas requería ~5,600 requests. El CSV directo reduce a 1 request por los datos filtrados, mucho más rápido. El `$limit=5000000` es el máximo que permite SODA — para el histórico completo habría que paginar por año o usar la API de descarga bulk.

---

### `ideam_temperatura.py` — Temperatura máxima IDEAM

**Qué hace:** Descarga temperatura máxima diaria del IDEAM (~27M filas total). Filtra últimos 5 años. Guarda en `data/raw/ideam_tmax.parquet`.

**Cómo lo hace:** Idéntico a precipitación pero con dataset `ccvq-rp9s`. Misma estrategia de CSV directo con filtro de fecha y `$limit`.

**Por qué así:** Misma razón que precipitación: el CSV directo con filtro es más simple y rápido que paginar 540 requests JSON. La simetría entre ambos scripts facilita el mantenimiento.

---

### `ideam_humedad.py` — Humedad relativa IDEAM

**Qué hace:** Descarga humedad relativa del aire (~87M filas total). Filtra últimos 5 años. Guarda en `data/raw/ideam_humedad.parquet`.

**Cómo lo hace:** Usa `_soda.fetch_soda()` con dataset `uext-mhny`, paginación determinista con `$order=fechaobservacion`.

**Por qué así:** Es un script más nuevo pero no migró a CSV directo porque no se probó aún si el endpoint CSV respeta `$order` para datasets grandes. Usa la paginación probada de `_soda.py`.

---

### `ideam_presion.py` — Presión atmosférica IDEAM

**Qué hace:** Descarga presión atmosférica (~34M filas total). Filtra últimos 5 años. Guarda en `data/raw/ideam_presion.parquet`.

**Cómo lo hace:** Usa `_soda.fetch_soda()` con dataset `62tk-nxj5` y filtro de fecha.

**Por qué así:** Misma razón que humedad — usa el cliente SODA estándar porque no se ha validado el CSV endpoint para este dataset.

---

### `ideam_tambiente.py` — Temperatura ambiente IDEAM

**Qué hace:** Descarga temperatura ambiente (media y mínima, ~90M filas total). Filtra últimos 5 años. Guarda en `data/raw/ideam_tambiente.parquet`.

**Cómo lo hace:** Usa `_soda.fetch_soda()` con dataset `sbwg-7ju4`.

**Por qué así:** Pendiente de migrar a CSV directo. Usa SODA paginado por consistencia.

---

### `eva.py` — Evaluaciones Agropecuarias Municipales

**Qué hace:** Descarga dos datasets del EVA (Evaluaciones Agropecuarias Municipales) del Ministerio de Agricultura: el principal (`2pnw-mmge`, ~200K filas) con área sembrada, cosechada, producción y rendimiento por municipio/año/cultivo, y la vista auxiliar (`fp29-z39g`, ~170 filas). Guarda `eva.parquet` y `eva_vista.parquet`.

**Cómo lo hace:** Usa `_soda.fetch_soda()` con cada dataset ID. El principal requiere paginación (~4 páginas de 50K).

**Por qué así:** SODA es la fuente oficial y el dataset cabe en ~4 páginas, así que no justifica un mecanismo especial. EVA es la base del subíndice de Exposición Productiva (SEP).

---

### `eva_calendario.py` — Calendario de siembra UPRA

**Qué hace:** Descarga el consolidado de calendarios de siembra y cosecha EVA desde la página de UPRA (Unidad de Planificación Rural Agropecuaria). Guarda en `data/raw/eva_calendario.parquet`.

**Cómo lo hace:** Descarga un archivo Excel (.xlsx) directamente desde `upra.gov.co` con `requests.get()`, lo lee con `pd.read_excel()`, elimina columnas `Unnamed`, normaliza nombres a minúsculas y fuerza texto en columnas de tipo mixto antes de guardar como Parquet.

**Por qué así:** UPRA publica el consolidado como Excel, no como dataset SODA. Intentar extraerlo de SODA daría datos desactualizados o incompletos. La descarga directa del Excel oficial es más confiable y simple.

---

### `insumos.py` — Índice de Insumos Agrícolas

**Qué hace:** Descarga el índice de precios de insumos agrícolas del DANE/UPRA (88 filas). Guarda en `data/raw/insumos.parquet`.

**Cómo lo hace:** Una sola página SODA con `_soda.fetch_soda()`, dataset `gwbi-fnzs`.

**Por qué así:** Es un dataset minúsculo. SODA es adecuado y no requiere optimización.

---

### `ideam_viento.py` — Velocidad del viento IDEAM

**Qué hace:** Descarga observaciones de velocidad del viento del IDEAM desde datos.gov.co (~600K filas, últimos 2 años). Guarda en `data/raw/ideam_viento.parquet`.

**Cómo lo hace:** Usa el endpoint JSON de SODA con `$order=fechaobservacion DESC`, paginación de 200K registros por página (hasta 3 páginas). El filtro `$where` limita a los últimos 2 años.

**Por qué así:** El endpoint CSV de SODA (usado por otros scripts) responde con error 400 para este dataset. El JSON endpoint es más confiable. No se descargan 169M filas históricas completas por límites de tiempo de respuesta; 600K registros (~12 días continuos) cubren las estaciones activas y permiten computar promedios mensuales representativos.

---

### `ndvi.py` — NDVI satelital MODIS

**Qué hace:** Descarga NDVI pre-agregado por municipio desde HDX (Humanitarian Data Exchange), dataset `colombia-ndvi-municipio`. Contiene 184K filas con NDVI medio mensual por municipio, 2022–2026. Guarda en `data/raw/ndvi.parquet`.

**Cómo lo hace:** Usa `requests.get()` para descargar un CSV desde HDX. Mapea códigos P-codes (ej. `CO05001`) a códigos DANE de 5 dígitos quitando el prefijo "CO".

**Por qué así:** HDX ofrece el dato ya agregado por municipio, evitando procesamiento geoespacial de imágenes raster MODIS (~500 GB). La resolución temporal mensual es adecuada para el modelo IRA.

---

### `dane_municipios.py` — Variables socioeconómicas DANE

**Qué hace:** Descarga NBI (Necesidades Básicas Insatisfechas) y población rural/urbana por municipio desde datos.gov.co. Guarda en `data/raw/dane_municipios.parquet`. Estas variables entran en el subíndice de Vulnerabilidad Económica (SVE).

**Cómo lo hace:** Usa `_soda.fetch_soda()` con dataset `fjhr-4qb9` y filtro por año más reciente.

**Por qué así:** No hay una API directa del DANE para estos indicadores. SODA ofrece el dataset oficial con la estructura tabular necesaria.

**Nota:** El dataset `fjhr-4qb9` fue retirado de datos.gov.co. El pipeline maneja el error cargando una tabla vacía. Las variables NBI quedan como NULL en `features_municipio_cultivo`.

---

### `load_duckdb.py` — Carga a DuckDB

**Qué hace:** Lee todos los archivos Parquet de `data/raw/` y los carga como tablas en `data/alerta.duckdb` con el prefijo `raw_`. Ejemplo: `ideam_precip.parquet` → `raw_precipitacion`.

**Cómo lo hace:** Conecta a DuckDB con extensión espacial, itera sobre una lista de pares `(archivo_parquet, nombre_tabla)`, y ejecuta `CREATE OR REPLACE TABLE raw_xxx AS SELECT * FROM read_parquet('...')`.

**Por qué así:** DuckDB es el motor analítico local — más rápido que pandas para consultas tipo SQL y soporta joins espaciales vía la extensión `spatial`. La carga con `CREATE OR REPLACE` asegura que las tablas siempre reflejen el último estado de `data/raw/`. Las extensiones `INSTALL spatial; LOAD spatial;` se ejecutan al conectar para permitir consultas geoespaciales en todos los módulos que usan `get_connection()`.

---

## Orden de ejecución

El orquestador (`scripts/run.py ingest`) corre los módulos en este orden:

```
estaciones  →  municipios  →  eva  →  eva_calendario  →  insumos  →  dane  →  dane_nbi  →
precipitacion  →  temperatura  →  humedad  →  presion  →  tambiente  →  viento  →  ndvi
```

Dependencias lógicas:
- `ideam_estaciones` + `igac_municipios` deben ejecutarse antes de `spatial.py` (en `src/features/`)
- EVA, insumos, DANE y DANE NBI son independientes y pueden correr en cualquier orden
- `load_duckdb.py` se corre después de toda la ingesta para consolidar en DuckDB
