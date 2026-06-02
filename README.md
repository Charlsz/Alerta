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
- Priorizar municipios, cultivos y zonas agrícolas vulnerables.
- Implementar modelos de analítica avanzada e inteligencia artificial para estimar riesgo climático agrícola.
- Desplegar una plataforma web para consulta, visualización y exploración de resultados.

## Alcance inicial

La solución se enfocará en:

- Integración de datos meteorológicos recientes e históricos.
- Uso de datos productivos agrícolas a nivel municipal.
- Incorporación de variables territoriales y cartografía oficial.
- Análisis geoespacial y generación de indicadores de riesgo.
- Visualización de resultados en una plataforma web con arquitectura monolítica modular.

## Fuentes de datos previstas

### Clima y meteorología
- IDEAM: precipitación, temperatura máxima, estaciones y eventos meteorológicos.
- CHIRPS: series históricas de precipitación.
- NASA POWER: variables climáticas complementarias.
- ERA5-Land: variables climáticas y de superficie.

### Producción agropecuaria
- EVA: área sembrada, área cosechada, producción y rendimiento.
- Agronet: estadísticas agrícolas y apoyo sectorial.
- UPRA: uso del suelo, aptitud y caracterización agropecuaria.

### Territorio y cartografía
- IGAC: cartografía oficial y variables territoriales.
- Colombia en Mapas: capas geográficas base para análisis espacial.

### Contexto socioeconómico
- DANE: variables socioeconómicas y de mercado.

### Observación satelital
- Sentinel-2: vegetación, cobertura y cambios en superficie.

## Herramientas y tecnologías

### Procesamiento y análisis
- Python
- Pandas
- GeoPandas
- NumPy
- Dask

### Infraestructura y análisis geoespacial
- PostgreSQL
- PostGIS
- QGIS
- Google Earth Engine

### Modelado y analítica avanzada
- Modelos de inteligencia artificial para estimación de riesgo climático agrícola
- Prithvi-EO-2.0 como referencia para exploración de modelado satelital avanzado

## Enfoque metodológico

El proyecto seguirá cuatro etapas principales:

1. **Integración de datos**  
   Recolección, limpieza, homologación y cruce de fuentes climáticas, productivas, territoriales y socioeconómicas.

2. **Construcción de variables**  
   Generación de indicadores de clima, exposición agrícola, contexto territorial y vulnerabilidad.

3. **Estimación de riesgo**  
   Aplicación de analítica avanzada e inteligencia artificial para estimar el riesgo climático agrícola.

4. **Visualización y priorización**  
   Desarrollo de una plataforma web para explorar resultados, visualizar mapas y priorizar municipios y cultivos.

## Equipo

Proyecto desarrollado en el marco de GovCamp 2026 y del reto:

**Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos.**

## Notas

Este repositorio documenta el desarrollo técnico y metodológico de la solución.  
El alcance, las fuentes y las herramientas podrán ajustarse durante la implementación según disponibilidad, calidad y utilidad analítica de los datos.


| Tipo                       | Dataset / Servicio                                                      | Qué aporta                                                                                                                | URL                                                                                                                     |
| -------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Producción agro            | Evaluaciones Agropecuarias Municipales – EVA (2007–2018) – datos.gov.co | Producción, área sembrada, cosechada y rendimiento agrícola a nivel municipal. datos.gov+1                                | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA/2pnw-mmge            |
| Producción agro            | EVA 2019–2023 Base Agrícola – uso oficial                               | Descripción y enlace a la base EVA reciente a nivel municipal (áreas, producción, rendimientos). herramientas.datos.gov+1 | http://herramientas.datos.gov.co/usos/evaluaciones-agropecuarias-municipales-eva-2019-2023-base-agricola                |
| Calendario cultivos        | EVA – Calendario Nacional de Siembras y Cosechas (2022)                 | Distribución mensual de áreas sembradas y cosechadas a nivel nacional por cultivo. datos.gov                              | https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA-Calenda/4229-puwp    |
| Clima observado            | Precipitación – IDEAM (s54a-sgyg)                                       | Datos crudos de precipitación de estaciones automáticas; serie temporal extensa descargable. datos.gov                    | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Precipitaci-n/s54a-sgyg                                       |
| Clima observado            | Temperatura Máxima del Aire – IDEAM (ccvq-rp9s)                         | Datos crudos de temperatura máxima a 2 m de estaciones automáticas. datos.gov                                             | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Temperatura-M-xima-del-Aire/ccvq-rp9s                         |
| Estaciones clima           | Catálogo Nacional de Estaciones del IDEAM                               | Listado de estaciones con código, tipo, categoría, coordenadas y otros atributos. datos+1                                 | https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Cat-logo-Nacional-de-Estaciones-del-IDEAM/hp9r-jxuu           |
| Clima satelital            | CHIRPS Daily Precipitation – Google Earth Engine                        | Serie diaria de precipitación 0.05° desde 1981 hasta casi tiempo real, diseñada para monitoreo de sequía. chc.ucsb+1      | https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY                                       |
| Clima reanálisis           | ERA5-Land Hourly – ECMWF / Earth Engine                                 | Reanálisis horario de variables de tierra (precipitación, temperatura, humedad, etc.) desde 1950. hal+2                   | https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY                                      |
| Clima global               | NASA POWER                                                              | API gratuita con más de 300 variables meteorológicas y de radiación para agricultura y energía. power.larc.nasa+2         | https://power.larc.nasa.gov                                                                                             |
| Estadísticas agro          | Agronet – Estadísticas                                                  | Portal con estadísticas de producción, áreas, rendimientos, precios y otros indicadores agropecuarios. agronet+1          | https://agronet.gov.co/estadisticas                                                                                     |
| Producción agro (síntesis) | EVA – UPRA                                                              | Sitio oficial EVA con documentación y acceso a resultados por municipio (área, producción, rendimiento). upra+1           | https://upra.gov.co/es-co/eva                                                                                           |
| Territorio / mapas         | Colombia en Mapas – IGAC                                                | Plataforma para descargar límites administrativos y otras capas en SHP, GeoJSON, CSV, etc. colombiaenmapas.gov+1          | https://www.colombiaenmapas.gov.co                                                                                      |
| Territorio / cartografía   | IGAC – Datos Abiertos Cartografía y Geografía                           | Catálogo de cartografía oficial descargable (suelos, límites, capas temáticas). geoportal.igac.gov+1                      | https://geoportal.igac.gov.co/contenido/datos-abiertos-cartografia-y-geografia                                          |
| Socioeconómico             | DANE – indicadores municipales                                          | Más de 1.300 indicadores territoriales para 1.102 municipios y 32 departamentos. dane.gov                                 | (presentación de indicadores) https://www.dane.gov.co/files/act-dane/conme-dia-p/pres-DICE-UsoDatosAbiertos-jul2023.pdf |
