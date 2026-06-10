# Alerta

Plataforma de alerta temprana para riesgo climático agrícola basada en datos abiertos, orientada a priorizar municipios, cultivos y zonas agrícolas vulnerables en Colombia.

## Descripción

Este proyecto propone una solución analítica y geoespacial para identificar riesgo climático agrícola mediante la integración de información meteorológica reciente, series históricas, datos productivos y variables territoriales.

La plataforma busca apoyar la toma de decisiones mediante la priorización de territorios y cultivos con mayor exposición y vulnerabilidad frente a condiciones climáticas adversas.

## Objetivo general

Desarrollar una plataforma de alerta temprana para riesgo climático agrícola que utilice datos abiertos para analizar, integrar y visualizar información climática, productiva y territorial a nivel municipal.

## Objetivos específicos

- Integrar fuentes de datos abiertas de clima, producción agropecuaria, territorio y contexto socioeconómico.
- Construir variables e indicadores para caracterizar riesgo climático agrícola.
- Priorizar municipios, cultivos y zonas agrícolas vulnerables mediante un Índice de Riesgo Agroclimático (IRA).
- Implementar modelos de analítica avanzada e inteligencia artificial para estimar riesgo climático agrícola.
- Desplegar una plataforma web para consulta, visualización y exploración de resultados.

## Alcance inicial

La solución se enfocará en:

- Integración de datos meteorológicos recientes e históricos (estaciones IDEAM + CHIRPS + ERA5-Land).
- Uso de datos productivos agrícolas a nivel municipal (EVA, Agronet, UPRA).
- Incorporación de variables territoriales, cartografía oficial y observación satelital (Sentinel-1 SAR, Sentinel-2).
- Análisis geoespacial y generación de indicadores de riesgo.
- Visualización de resultados en una plataforma web con arquitectura monolítica modular (FastAPI + React).

## Metodología del Índice de Riesgo Agroclimático (IRA)

El IRA combina tres sub-índices para producir un score de riesgo por municipio y cultivo:

### Sub-índices

**1. Sub-índice de Peligro Climático (SPC)**  
Mide la intensidad y anomalía de las condiciones meteorológicas respecto al histórico:
- Anomalía de precipitación acumulada (7 y 30 días vs. histórico CHIRPS/IDEAM).
- Número de días secos consecutivos.
- Número de días con precipitación por encima del umbral de lluvia extrema.
- Anomalía de temperatura máxima vs. histórico.
- Número de días con temperatura máxima por encima del umbral crítico por cultivo.
- Índice de humedad del suelo derivado de Sentinel-1 SAR (cuando disponible).

**2. Sub-índice de Exposición Productiva (SEP)**  
Mide la importancia agrícola del municipio y su dependencia del cultivo analizado:
- Área sembrada y cosechada por cultivo (EVA).
- Participación del cultivo en la producción municipal y nacional.
- Varianza histórica del rendimiento (estabilidad productiva).
- Fase fenológica activa según calendario de siembras y cosechas (EVA Calendario).

**3. Sub-índice de Vulnerabilidad Económica (SVE)**  
Mide la capacidad de respuesta y el contexto socioeconómico:
- Nivel e índice de precios de insumos agrícolas (UPRA).
- Anomalía del índice de insumos vs. promedio 12 meses.
- Variables socioeconómicas municipales (DANE).

### Fórmula del IRA

```
IRA = w1 × SPC + w2 × SEP + w3 × SVE
```

Donde w1, w2, w3 son ponderaciones a definir y calibrar durante la fase de construcción de variables. Los valores iniciales propuestos son w1=0.5, w2=0.3, w3=0.2.

Cada sub-índice se normaliza entre 0 y 1 antes de combinarlos. El IRA final se clasifica en cuatro niveles: **Bajo (0–0.25)**, **Medio (0.25–0.50)**, **Alto (0.50–0.75)** y **Crítico (0.75–1.0)**.

### Componente de IA

Sobre el IRA base se aplica un modelo de detección de anomalías multivariadas (IsolationForest o clustering) entrenado por cultivo o región para identificar municipios que presentan combinaciones inusuales de variables climáticas, productivas y económicas. La explicabilidad del modelo se implementa con importancia de variables (SHAP), permitiendo al usuario final entender qué factores disparan la alerta en cada municipio.

Prithvi-EO-2.0 se evalúa como modelo fundacional para procesamiento de imágenes satelitales Sentinel-2 (clasificación de cobertura, detección de cambios). Su incorporación depende de la viabilidad técnica durante el desarrollo.

## Fuentes de datos previstas

### Clima y meteorología
- **IDEAM** – Precipitación, temperatura máxima, catálogo de estaciones y eventos meteorológicos.
- **CHIRPS** – Series históricas de precipitación desde 1981, resolución ~5.5 km, cobertura total de Colombia.
- **NASA POWER** – Variables climáticas complementarias (radiación, humedad relativa, viento).
- **ERA5-Land** – Variables climáticas y de superficie de largo plazo (reanálisis).

### Observación satelital
- **Sentinel-2** – Índices de vegetación (NDVI), cobertura del suelo y cambios superficiales (sensor óptico).
- **Sentinel-1 SAR** – Humedad del suelo, detección de inundaciones en zonas agrícolas (sensor radar, funciona con cobertura nubosa).

### Producción agropecuaria
- **EVA** – Área sembrada, área cosechada, producción y rendimiento por municipio y cultivo.
- **EVA Calendario** – Distribución mensual de siembras y cosechas por cultivo.
- **Agronet** – Estadísticas agrícolas complementarias.
- **UPRA** – Uso del suelo, aptitud y caracterización agropecuaria; índice de precios de insumos.

### Territorio y cartografía
- **IGAC** – Cartografía oficial, límites municipales y variables territoriales.
- **Colombia en Mapas** – Capas geográficas base para visualización y cruces espaciales.

### Contexto socioeconómico
- **DANE** – Variables socioeconómicas y de mercado a nivel municipal.

### Referencias metodológicas
- **Alliance Bioversity–CIAT** – Investigación sobre vulnerabilidad climática agrícola en Colombia y metodologías de índices de riesgo por cultivo.

## Herramientas y tecnologías

### Procesamiento y análisis de datos
- Python 3.10+
- Pandas / Polars (volúmenes grandes)
- GeoPandas + Shapely
- NumPy
- Dask

### Infraestructura y análisis geoespacial
- PostgreSQL + PostGIS
- QGIS (validación de capas y visualización offline)
- Google Earth Engine (procesamiento satelital Sentinel-1 y Sentinel-2)

### Modelado y analítica avanzada
- Scikit-learn (IsolationForest, clustering, modelos de clasificación)
- SHAP (explicabilidad de modelos)
- Prithvi-EO-2.0 (exploración para clasificación satelital avanzada)

### Backend y API
- FastAPI
- SQLAlchemy / GeoAlchemy2

### Frontend y visualización
- React + Vite
- Leaflet / MapLibre (mapas interactivos)
- Chart.js / Plotly (series temporales y gráficos)

## Enfoque metodológico

El proyecto seguirá cuatro etapas principales:

1. **Integración de datos**  
   Recolección, limpieza, homologación y cruce de fuentes climáticas, productivas, territoriales y socioeconómicas. Join municipal como unidad base de análisis.

2. **Construcción de variables**  
   Generación de los tres sub-índices (SPC, SEP, SVE) y sus variables componentes. Normalización y validación espacial en QGIS.

3. **Estimación de riesgo**  
   Cálculo del IRA ponderado y aplicación del modelo de anomalías multivariadas con explicabilidad SHAP.

4. **Visualización y priorización**  
   Plataforma web con mapa de riesgo municipal, ranking de municipios–cultivo, ficha por municipio con explicación de variables y series temporales.

### Reto: Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos.

## Links / datos encontrados

| Tipo | Dataset / Servicio | Qué aporta | URL |
|---|---|---|---|
| Producción agro | Evaluaciones Agropecuarias Municipales EVA | Base histórica de producción agrícola, áreas sembradas, cosechadas y rendimiento. | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA/2pnw-mmge |
| Producción agro | Vista EVA | Vista actualizada con resultados estadísticos por municipio. | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Vista-Evaluaciones-Agropecuarias-Municipales-EVA/fp29-z39g |
| Calendario cultivos | Consolidado calendarios EVA 2024 – UPRA | Archivo Excel consolidado con calendarios EVA 2024. | https://upra.gov.co/sites/default/files/2025-08/Consolidado%20calendarios%20EVA%202024.xlsx |
| Clima histórico | CHIRPS | Series de precipitación desde 1981, resolución ~5.5 km, cubre toda Colombia sin depender de estaciones físicas. | https://www.chc.ucsb.edu/data/chirps |
| Observación satelital | Sentinel-1 SAR – NASA Earthdata | Humedad del suelo e inundaciones; funciona con cobertura nubosa (radar). | https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar |
| Territorio / cartografía | IGAC – Datos Abiertos | Cartografía oficial descargable. | https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia |
| Referencia metodológica | Alliance Bioversity–CIAT | Investigación y metodologías sobre vulnerabilidad climática agrícola en Colombia. | https://alliancebioversityciat.org/es |

| Tipo | URL | Cantidad |
|---|---|---|
|Presión Atmosférica	| https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Presi-n-Atmosf-rica/62tk-nxj5/about_data | "Filas 33,9M Columnas 12" |
|Deforestación por año | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Deforestaci-n-por-a-o/cqcx-tjpz | "Datos modificados (7025 de filas) Todos los datos (7937 filas)" |
|Temperatura Ambiente del Aire | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-Ambiente-del-Aire/sbwg-7ju4/about_data | "Filas 90,3M Columnas12" |
|Precipitación y Precipitaciones | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaci-n/s54a-sgyg/about_data - precipitacion | "Filas 280M Columnas 12"|
|Precipitación y Precipitaciones | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaciones/ksew-j3zj - precipitaciones | Todos los datos (280301628 filas)
|Velocidad del Viento | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Velocidad-del-Viento/sgfv-3yp8/about_data | "Filas 169M Columnas 12"|
|Temperatura Máxima del Aire | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-M-xima-del-Aire/ccvq-rp9s/about_data | "Filas 26,8M Columnas 12"|
|Humedad del Aire	| https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Humedad-del-Aire/uext-mhny/about_data | "Filas 86,8M Columnas 12"|
|Causas de Deforestación | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Causas-de-Deforestaci-n/em23-mwhw | "Datos modificados (7583 de filas) Todos los datos (7937 filas)" |

## Notas

Este repositorio documenta el desarrollo técnico y metodológico de la solución.  
El alcance, las fuentes y las herramientas podrán ajustarse durante la implementación según disponibilidad, calidad y utilidad analítica de los datos.
