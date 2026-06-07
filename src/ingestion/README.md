# Ingesta de datos (src/ingestion)

Este módulo descarga los datos crudos de cada fuente externa y los guarda en `data/raw/` como archivos Parquet. Cada script es independiente, idempotente y sigue el mismo patrón.

## Archivos creados

| Archivo | Fuente | Salida |
|---|---|---|
| `ideam_estaciones.py` | Catálogo estaciones IDEAM (hp9r-jxuu) | `data/raw/ideam_estaciones.parquet` |
| `eva.py` | EVA – datos.gov.co (2pnw-mmge + fp29-z39g) | `data/raw/eva.parquet` + `eva_vista.parquet` |
| `eva_calendario.py` | EVA Calendario 2023–2024 (4229-puwp) | `data/raw/eva_calendario.parquet` |
| `ideam_precipitacion.py` | Precipitación IDEAM (s54a-sgyg) | `data/raw/ideam_precip.parquet` |
| `ideam_temperatura.py` | Temperatura Máxima IDEAM (ccvq-rp9s) | `data/raw/ideam_tmax.parquet` |
| `insumos.py` | Índice de insumos agrícolas UPRA (gwbi-fnzs) | `data/raw/insumos.parquet` |

## Cómo funciona cada script

1. **Paginación SODA API** – Usa `$limit` y `$offset` según `config.soda_page_size` (por defecto 50 000).
2. **Filtro de fecha** – Los datasets grandes de IDEAM (precipitación y temperatura) filtran por los últimos 5 años vía `$where=fechaobservacion >= 'YYYY-MM-DD'` para no descargar millones de filas históricas.
3. **Idempotencia** – Si el archivo Parquet ya existe, el script se salta la descarga a menos que se use `--force`.
4. **Logging** – Se loguea cuántas filas se descargaron, el rango de fechas (cuando aplica) y cualquier error de red como `warning` sin detener el pipeline.
5. **Token opcional** – Si existe la variable de entorno `SODA_APP_TOKEN`, se envía en el header `X-App-Token` para aumentar el rate limit.

## Cómo probar

### Ejecutar un script individual

```bash
# Desde la raíz del proyecto
python src/ingestion/eva.py
python src/ingestion/ideam_precipitacion.py
```

Forzar re-descarga:

```bash
python src/ingestion/eva.py --force
```

### Ejecutar todo el pipeline de ingesta

```bash
python scripts/run_ingestion.py
```

Con `--force` para todos los datasets:

```bash
python scripts/run_ingestion.py --force
```

`run_ingestion.py` ejecuta los módulos en este orden:

1. `ideam_estaciones`
2. `eva`
3. `eva_calendario`
4. `ideam_precipitacion`
5. `ideam_temperatura`
6. `insumos`

Si alguno falla, se loguea el error y el pipeline **continúa** con el siguiente módulo; no se detiene.

## Variables de entorno

Copia `.env.example` a `.env` y, si tienes uno, añade tu token de Socrata:

```bash
SODA_APP_TOKEN=tu_token_aqui
```

Sin token el script funciona igual, pero el rate limit es más bajo.

## Nota sobre volúmenes

- **Precipitación IDEAM:** ~280 M filas totales. El script descarga solo los últimos 5 años.
- **Temperatura IDEAM:** ~27 M filas totales. Igual estrategia de filtro por fecha.
- El resto de datasets son pequeños y se descargan completos sin filtro adicional.
