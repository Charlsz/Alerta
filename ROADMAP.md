# Roadmap

Lo que falta para completar el proyecto según la visión de Alerta. Priorizado por impacto y esfuerzo.

## Crítico — Datos rotos o ausentes

### 1. Reemplazar CHIRPS con NASA POWER o ERA5-Land

**Problema:** CHIRPS cambió su formato de distribución a un único archivo NetCDF combinado de ~7.7 GB. El pipeline actual no puede procesarlo. `precip_anomalia_30d` es NULL en todas las filas.

**Camino sugerido:**
1. Evaluar dos alternativas:
   - **NASA POWER API**: consultas por punto (lat, lon), requiere una llamada por centroide de municipio (1.122 requests).
   - **ERA5-Land** vía Copernicus CDS (`cdsapi`): un solo request para toda Colombia en bounding box.
2. Crear `src/ingestion/nasa_power.py` o adaptar `src/ingestion/chirps.py` para usar la nueva fuente.
3. Actualizar `src/features/clima.py` para leer de la nueva tabla.
4. Verificar que `precip_anomalia_30d` tenga valores en DuckDB.

**Archivos a tocar:** `src/ingestion/chirps.py`, `src/features/clima.py`, `scripts/run.py`

---

### 2. Parche DANE NBI

**Problema:** El dataset `fjhr-4qb9` fue eliminado de datos.gov.co. `nbi_total`, `poblacion_rural` y `pct_rural` son NULL, lo que degrada el sub-índice SVE.

**Camino sugerido:**
1. Descargar el Excel de NBI 2018 desde la página del DANE (Estadísticas → Pobreza → NBI).
2. Crear `src/ingestion/dane_nbi.py` que lea el Excel y lo guarde como parquet con `codigo_municipio` en formato DANE de 5 dígitos.
3. Actualizar `src/features/vulnerabilidad.py` para leer de la nueva tabla en lugar de `clean_dane_municipios`.
4. Confirmar que `nbi_total` y `pct_rural` tengan valores reales en `features_municipio_cultivo`.

**Archivos a tocar:** `src/ingestion/dane_nbi.py` (nuevo), `src/features/vulnerabilidad.py`, `scripts/run.py`

---

### 3. Viento IDEAM

**Problema:** Es el sexto dataset climático del IDEAM. Existe en `datos.gov.co` con ID `sgfv-3yp8` (169M filas) pero nunca se implementó el script de ingesta.

**Camino sugerido:**
1. Copiar `src/ingestion/ideam_humedad.py` → `src/ingestion/ideam_viento.py`.
2. Cambiar dataset ID a `sgfv-3yp8`, tabla a `raw_viento`.
3. Agregar al orquestador en `scripts/run.py`.
4. En `src/features/clima.py`, agregar `viento_media_7d` y `viento_anomalia_30d` siguiendo el patrón de humedad.
5. Agregar las nuevas variables al SPC en `src/risk/ira.py` y a la lista de predictores en `normalize.py`.

**Archivos a tocar:** `src/ingestion/ideam_viento.py` (nuevo), `src/features/clima.py`, `src/risk/ira.py`, `src/features/normalize.py`, `scripts/run.py`

---

## Medio — Mejora de calidad del modelo

### 4. Instalar XGBoost

**Problema:** El pipeline detecta si XGBoost está instalado. Si no, usa RandomForestRegressor como fallback. Con XGBoost los modelos de predicción de rendimiento serían más precisos.

**Camino sugerido:**
```bash
pip install xgboost
```
El pipeline lo usa automáticamente. No requiere cambios de código.

**Archivos a tocar:** `requirements.txt`

---

### 5. Calibrar pesos del IRA con datos reales

**Problema:** Hoy los pesos del IRA son fijos (SPC=0.5, SEP=0.3, SVE=0.2) definidos en `config.py`. Idealmente deberían calibrarse con datos históricos de pérdidas agrícolas reales.

**Camino sugerido:**
1. Buscar el reporte de pérdidas agrícolas históricas del MADR (Excel público con pérdidas por municipio, año y cultivo).
2. Crear un script que cruce las pérdidas reportadas vs. el IRA calculado para ese período.
3. Ajustar los pesos para maximizar correlación entre IRA alto y pérdida real observada.
4. Actualizar `config.py` con los nuevos pesos.

**Nota:** Este paso puede requerir investigación externa para localizar el dataset adecuado. No hay una fuente limpia conocida en datos.gov.co.

**Archivos a tocar:** `config.py`, script de calibración nuevo

---

### 6. Deforestación (2 datasets)

**Problema:** Los datasets `cqcx-tjpz` (deforestación por año) y `em23-mwhw` (causas de deforestación) están identificados pero no se descargan ni integran.

**Camino sugerido:**
1. Verificar que tengan columna `codigo_municipio` en formato DANE 5 dígitos (muchos datasets ambientales usan solo nombre).
2. Crear `src/ingestion/deforestacion.py` con `fetch_soda("cqcx-tjpz")`.
3. Agregar variables `tasa_deforestacion` y `causa_principal` al SVE.
4. Agregar al orquestador.

**Archivos a tocar:** `src/ingestion/deforestacion.py` (nuevo), `src/features/vulnerabilidad.py`, `scripts/run.py`

---

## Bajo — Frontend y UX

### 7. Mostrar SHAP y tendencias en la UI

**Problema:** `importancia_top3` se calcula en `predict_rendimiento.py` y se guarda en `ira_resultados`, pero el frontend no lo renderiza. Tampoco hay gráfico de tendencia de los últimos 4 trimestres.

**Camino sugerido:**
1. En `MunicipioCard.jsx`, agregar sección que muestre las top-3 variables de `importancia_top3` (parseando el JSON).
2. En `MunicipioCard.jsx`, agregar un chart simple con los datos históricos del municipio (todos los períodos disponibles).
3. Agregar filtro por trimestre en `FilterBar.jsx`.

**Archivos a tocar:** `src/web/app/components/MunicipioCard.jsx`, `src/web/app/components/FilterBar.jsx`

---

### 8. Despliegue público

**Problema:** Hoy el proyecto corre solo en localhost. Para cumplir el objetivo del concurso necesita ser accesible sin conocimientos técnicos.

**Camino sugerido:**
1. Unificar API + frontend en `docker-compose.yml`.
2. Desplegar en Render, Railway o VPS propio.
3. Configurar dominio (opcional).
4. Agregar GitHub Actions que verifique que el deploy no se rompe.

---

## Automatización

### 9. Pipeline automático semanal

**Problema:** Hoy el pipeline corre manualmente con `python scripts/run.py`. Para que sea autónomo necesita un scheduler.

**Camino sugerido:**
1. Crear `.github/workflows/pipeline.yml` con trigger `cron: '0 5 * * 1'`.
2. Alternativa: cron en el servidor de despliegue que ejecute `make pipeline`.

**Nota:** GitHub Actions no es práctico para el pipeline completo (datos grandes, sin persistencia entre runs). Un cron en el servidor de despliegue es más realista.

---

## Resumen de esfuerzo

| Prioridad | Tarea | Esfuerzo estimado | Dependencias |
|---|---|---|---|
| Crítico | NASA POWER / ERA5-Land | 2-3 días | Investigar API |
| Crítico | DANE NBI | 1 día | Descargar Excel |
| Crítico | Viento IDEAM | 1 día | Ninguna |
| Medio | XGBoost | 5 minutos | Ninguna |
| Medio | Calibrar pesos IRA | 3-5 días | Encontrar dataset MADR |
| Medio | Deforestación | 1 día | Verificar columnas |
| Bajo | SHAP + tendencias UI | 2 días | Ninguna |
| Bajo | Despliegue público | 1-2 días | Docker |
| Bajo | Pipeline automático | 1 día | Despliegue previo |
