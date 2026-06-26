"""Sistema multi-agente para análisis de riesgo agrícola.

Cada agente es un dict de configuración; un solo loop aplica umbrales.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_AGENTES = [
    dict(
        name="Clima", field="spc",
        desc="Analiza el peligro climático (SPC) y sus componentes",
        hallazgos={
            "crítico": ["Precipitación extrema o sequía prolongada", "Temperaturas fuera del rango óptimo para cultivos"],
            "alto": ["Condiciones climáticas adversas significativas"],
            "medio": ["Variabilidad climática moderada"],
        },
        recs={
            "crítico": ["Implementar sistemas de riego y drenaje", "Usar coberturas vegetales para proteger el suelo", "Monitorear pronósticos climáticos semanalmente"],
            "alto": ["Implementar sistemas de riego y drenaje", "Usar coberturas vegetales para proteger el suelo", "Monitorear pronósticos climáticos semanalmente"],
            "medio": ["Mantener calendario de monitoreo climático"],
        },
    ),
    dict(
        name="Producción", field="sep",
        desc="Analiza la exposición productiva (SEP) del municipio",
        hallazgos={
            "crítico": ["Alta dependencia productiva en {cultivo}", "Baja diversificación agrícola"],
            "alto": ["Exposición significativa en {cultivo}"],
            "medio": ["Dependencia moderada en {cultivo}"],
        },
        recs={
            "crítico": ["Diversificar cultivos para reducir riesgo", "Explorar mercados alternativos", "Fortalecer cadenas de valor locales"],
            "alto": ["Diversificar cultivos para reducir riesgo", "Explorar mercados alternativos", "Fortalecer cadenas de valor locales"],
            "medio": ["Evaluar rotación de cultivos"],
        },
    ),
    dict(
        name="Vulnerabilidad", field="sve",
        desc="Analiza la vulnerabilidad socioeconómica (SVE)",
        hallazgos={
            "crítico": ["Alto índice de necesidades básicas insatisfechas", "Población rural vulnerable"],
            "alto": ["Vulnerabilidad económica significativa"],
            "medio": ["Vulnerabilidad económica moderada"],
        },
        recs={
            "crítico": ["Gestionar subsidios y apoyos directos a productores", "Fortalecer programas de asistencia técnica rural", "Promover asociaciones de productores"],
            "alto": ["Gestionar subsidios y apoyos directos a productores", "Fortalecer programas de asistencia técnica rural", "Promover asociaciones de productores"],
            "medio": ["Mantener programas de capacitación agrícola"],
        },
    ),
]


def _nivel(valor: float | None) -> str:
    if valor is None:
        return "bajo"
    if valor > 0.75:
        return "crítico"
    if valor > 0.50:
        return "alto"
    if valor > 0.25:
        return "medio"
    return "bajo"


def analyze(row: dict[str, Any]) -> dict[str, Any]:
    cultivo = row.get("cultivo", "desconocido")
    agentes = []
    todas_recs: list[str] = []

    for cfg in _AGENTES:
        valor = row.get(cfg["field"])
        nivel = _nivel(valor)
        hallazgos = [h.format(cultivo=cultivo) for h in cfg["hallazgos"].get(nivel, [])]
        recomendaciones = cfg["recs"].get(nivel, [])[:]

        # Edge case: Producción también mira rendimiento_predicho
        if cfg["field"] == "sep":
            rend = row.get("rendimiento_predicho")
            if rend is not None and rend < 5:
                hallazgos.append("Rendimiento esperado bajo")

        for r in recomendaciones:
            if r not in todas_recs:
                todas_recs.append(r)

        agentes.append({
            "agente": cfg["name"],
            "descripcion": cfg["desc"],
            cfg["field"]: valor,
            "nivel": nivel,
            "hallazgos": hallazgos,
            "recomendaciones": recomendaciones,
        })

    niveles = [a["nivel"] for a in agentes]
    prioridad = max(niveles, key=lambda x: ["bajo", "medio", "alto", "crítico"].index(x))

    prioridad_map = {
        "crítico": "Se requiere acción inmediata. Todos los indicadores de riesgo están elevados.",
        "alto": "Se recomienda intervención prioritaria. Varios factores de riesgo requieren atención.",
        "medio": "Monitoreo regular recomendado. Algunos indicadores requieren seguimiento.",
        "bajo": "Condiciones favorables. Mantener monitoreo de rutina.",
    }

    return {
        "agentes": agentes,
        "coordinador": {
            "agente": "Coordinador",
            "descripcion": "Sintetiza los análisis de todos los agentes",
            "prioridad": prioridad,
            "resumen": prioridad_map.get(prioridad, ""),
            "recomendaciones_sintetizadas": todas_recs[:5],
        },
    }
