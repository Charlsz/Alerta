# src/ingestion/

Descarga los datos crudos de cada fuente y los guarda en `data/raw/`. Cada script es independiente, idempotente y sigue el mismo patrón.

---

## Archivos y salidas

| Archivo | Fuente | Salida en `data/raw/` |
|---|---|---|
| `ideam_estaciones.py` | Catálogo estaciones IDEAM (`hp9r-jxuu`) | `ideam_estaciones.parquet` |
| `igac_municipios.py` | Capa municipios Colombia — DANE/IGAC | `municipios.gpkg` |
| `eva.py` | EVA – datos.gov.co (`2pnw-mmge`, `fp29-z39g`) | `eva.parquet`, `eva_vista.parquet` |
| `eva_calendario.py` | EVA Calendario 2023–2024 (`4229-puwp`) | `eva_calendario.parquet` |
| `insumos.py` | Índice precios insumos agrícolas (`gwbi-fnzs`) | `insumos.parquet` |
| `ideam_precipitacion.py` | Precipitación IDEAM (`s54a-sgyg`) | `ideam_precip.parquet` |
| `ideam_temperatura.py` | Temperatura Máxima IDEAM (`ccvq-rp9s`) | `ideam_tmax.parquet` |
| `chirps.py` | CHIRPS v2.0 mensual (`chc.ucsb.edu`) | `chirps/<año>/<mes>.nc` |

---

## Módulo compartido: `_soda.py`

Todos los scripts que consumen la API SODA (datos.gov.co) usan `fetch_soda()` de `_soda.py`.
Esto evita duplicar el cliente HTTP y garantiza comportamiento uniforme:
- Paginación automática con `$limit` / `$offset`
- Token `X-App-Token` si `SODA_APP_TOKEN` está en el entorno
- `$where` y `$order` opcionales para filtrar y ordenar

---

## Patrón de cada script

1. **Idempotente**: si el archivo ya existe, no descarga de nuevo (salvo `--force`).
2. **Sin lógica de negocio**: solo descarga y persiste. La limpieza ocurre en `src/features/`.
3. **Errores como warnings**: los fallos de red se loguean y no detienen el pipeline.
4. **Instancia global `config`**: todos importan `from config import config` (no instancian `IRAConfig` localmente).

---

## Correr la ingesta

```bash
# Todo el pipeline en orden
python scripts/run_ingestion.py

# Forzar re-descarga de todo
python scripts/run_ingestion.py --force

# Solo un módulo
python scripts/run_ingestion.py --only eva
python scripts/run_ingestion.py --only precipitacion

# Script individual
python src/ingestion/ideam_estaciones.py
python src/ingestion/eva.py --force
```

---

## Orden de ejecución

El orquestador `scripts/run_ingestion.py` corre los pasos en este orden:

```
1. estaciones    — pequeño, necesario para joins espaciales
2. municipios    — shapefile DANE, necesario para spatial.py
3. eva           — producción agrícola municipal
4. eva_calendario— periodos de siembra y cosecha
5. insumos       — índice mensual nacional (muy pequeño)
6. precipitacion — ~280 M filas totales, filtrado a 5 años
7. temperatura   — ~27 M filas totales, filtrado a 5 años
8. chirps        — NetCDF mensuales desde 1991 (~400 MB)
```

Si un paso falla, se loguea el error y el pipeline **continúa** con el siguiente.

---

## Notas sobre volúmenes

- **Precipitación IDEAM**: ~280 M filas totales. El script filtra `fechaobservacion >= hace 5 años`.
- **Temperatura IDEAM**: ~27 M filas totales. Misma estrategia.
- **CHIRPS**: ~420 archivos NetCDF mensuales (1991–2026), ~1 MB por archivo. Descarga por streaming.
- El resto son datasets pequeños que se descargan completos.

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `SODA_APP_TOKEN` | No | Token Socrata para mayor rate limit en datos.gov.co |
