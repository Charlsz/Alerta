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

### Plataforma
- Arquitectura monolítica modular
- API backend para consulta de datos y resultados
- Aplicación web para visualización geoespacial y priorización territorial

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

## Estado del proyecto

Fase inicial de planeación y organización técnica.

Las siguientes tareas inmediatas son:

- Definir datasets núcleo de la primera versión.
- Crear el flujo inicial de ingestión y limpieza de datos.
- Estructurar el modelo de datos geoespacial.
- Diseñar la primera versión del indicador de riesgo.
- Construir el MVP de visualización territorial.

## Equipo

Proyecto desarrollado en el marco de GovCamp 2026 y del reto:

**Agricultura y Desarrollo Rural – Implementar modelos de IA para predecir rendimientos agrícolas y riesgos climáticos.**

## Notas

Este repositorio documenta el desarrollo técnico y metodológico de la solución.  
El alcance, las fuentes y las herramientas podrán ajustarse durante la implementación según disponibilidad, calidad y utilidad analítica de los datos.
