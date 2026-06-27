# src/features/ — Feature engineering

Construye variables e indicadores a partir de las tablas limpias en DuckDB.
Cada módulo expone `build(force=False)` que crea una tabla en DuckDB.

Salida final: tabla `features_municipio_cultivo` con 26 variables (14 SPC + 6 SEP + 6 SVE). Además produce tablas auxiliares `features_ndvi`, `features_deforestacion`, `features_dane` y `features_clima` (15 vars SPC, incl. viento).

## Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `clean.py` | 77 | Crea tablas `clean_*` en DuckDB desde `raw_*` con columnas normalizadas y tipos correctos |
| `clima.py` | 293 | Construye 15 variables climáticas SPC (incl. viento) por municipio × mes desde IDEAM |
| `deforestacion.py` | 224 | Pérdida de cobertura arbórea (GFW/Hansen) por municipio (2001–2025) |
| `municipio_lookup.py` | 160 | Homologación nombre_municipio → código DANE desde estaciones + IGAC |
| `ndvi.py` | 54 | NDVI medio mensual + anomalía desde MODIS (HDX) |
| `normalize.py` | 76 | Normalización min-max robusta (p1–p99) para las 26 variables |
| `produccion.py` | 99 | Construye 6 variables SEP (área, rendimiento, participación, fase fenológica) |
| `spatial.py` | 114 | Join espacial estaciones IDEAM → municipios; crea `estaciones_municipio` y `municipios_geom` |
| `store.py` | 98 | Une clima + producción + vulnerabilidad en la tabla maestra (26 variables) |
| `vulnerabilidad.py` | 114 | Construye 6 variables SVE (insumos agrícolas + DANE socioeconómico) |
