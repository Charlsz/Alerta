"""Sistema multi-agente para análisis de riesgo agrícola.

Agentes especializados analizan cada dimensión del IRA y un coordinador
sintetiza los hallazgos en una recomendación final.

Arquitectura:
    ClimateAgent      → analiza SPC (peligro climático)
    ExposureAgent     → analiza SEP (exposición productiva)
    VulnerabilityAgent → analiza SVE (vulnerabilidad económica)
    CoordinatorAgent  → orquesta y sintetiza
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Agentes base
# ─────────────────────────────────────────────────────────────────────────────

class BaseAgent:
    name: str = ""
    description: str = ""

    def analyze(self, row: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class ClimateAgent(BaseAgent):
    name = "Clima"
    description = "Analiza el peligro climático (SPC) y sus componentes"

    def analyze(self, row: dict[str, Any]) -> dict[str, Any]:
        spc = row.get("spc")
        findings = []
        nivel = "bajo"
        if spc is not None:
            if spc > 0.75:
                nivel = "crítico"
                findings.append("Precipitación extrema o sequía prolongada")
                findings.append("Temperaturas fuera del rango óptimo para cultivos")
            elif spc > 0.50:
                nivel = "alto"
                findings.append("Condiciones climáticas adversas significativas")
            elif spc > 0.25:
                nivel = "medio"
                findings.append("Variabilidad climática moderada")

        recomendaciones = []
        if nivel in ("crítico", "alto"):
            recomendaciones.append("Implementar sistemas de riego y drenaje")
            recomendaciones.append("Usar coberturas vegetales para proteger el suelo")
            recomendaciones.append("Monitorear pronósticos climáticos semanalmente")
        elif nivel == "medio":
            recomendaciones.append("Mantener calendario de monitoreo climático")

        return {
            "agente": self.name,
            "descripcion": self.description,
            "spc": spc,
            "nivel": nivel,
            "hallazgos": findings,
            "recomendaciones": recomendaciones,
        }


class ExposureAgent(BaseAgent):
    name = "Producción"
    description = "Analiza la exposición productiva (SEP) del municipio"

    def analyze(self, row: dict[str, Any]) -> dict[str, Any]:
        sep = row.get("sep")
        findings = []
        nivel = "bajo"

        cultivo = row.get("cultivo", "desconocido")
        rendimiento = row.get("rendimiento_predicho")

        if sep is not None:
            if sep > 0.75:
                nivel = "crítico"
                findings.append(f"Alta dependencia productiva en {cultivo}")
                findings.append("Baja diversificación agrícola")
            elif sep > 0.50:
                nivel = "alto"
                findings.append(f"Exposición significativa en {cultivo}")
            elif sep > 0.25:
                nivel = "medio"
                findings.append(f"Dependencia moderada en {cultivo}")

        if rendimiento is not None and rendimiento < 5:
            findings.append("Rendimiento esperado bajo")

        recomendaciones = []
        if nivel in ("crítico", "alto"):
            recomendaciones.append("Diversificar cultivos para reducir riesgo")
            recomendaciones.append("Explorar mercados alternativos")
            recomendaciones.append("Fortalecer cadenas de valor locales")
        elif nivel == "medio":
            recomendaciones.append("Evaluar rotación de cultivos")

        return {
            "agente": self.name,
            "descripcion": self.description,
            "sep": sep,
            "nivel": nivel,
            "hallazgos": findings,
            "recomendaciones": recomendaciones,
        }


class VulnerabilityAgent(BaseAgent):
    name = "Vulnerabilidad"
    description = "Analiza la vulnerabilidad socioeconómica (SVE)"

    def analyze(self, row: dict[str, Any]) -> dict[str, Any]:
        sve = row.get("sve")
        findings = []
        nivel = "bajo"

        if sve is not None:
            if sve > 0.75:
                nivel = "crítico"
                findings.append("Alto índice de necesidades básicas insatisfechas")
                findings.append("Población rural vulnerable")
            elif sve > 0.50:
                nivel = "alto"
                findings.append("Vulnerabilidad económica significativa")
            elif sve > 0.25:
                nivel = "medio"
                findings.append("Vulnerabilidad económica moderada")

        recomendaciones = []
        if nivel in ("crítico", "alto"):
            recomendaciones.append("Gestionar subsidios y apoyos directos a productores")
            recomendaciones.append("Fortalecer programas de asistencia técnica rural")
            recomendaciones.append("Promover asociaciones de productores")
        elif nivel == "medio":
            recomendaciones.append("Mantener programas de capacitación agrícola")

        return {
            "agente": self.name,
            "descripcion": self.description,
            "sve": sve,
            "nivel": nivel,
            "hallazgos": findings,
            "recomendaciones": recomendaciones,
        }


class CoordinatorAgent(BaseAgent):
    name = "Coordinador"
    description = "Sintetiza los análisis de todos los agentes"

    def analyze(self, row: dict[str, Any],
                agentes: list[dict[str, Any]]) -> dict[str, Any]:
        niveles = [a["nivel"] for a in agentes]
        prioridad = max(niveles, key=lambda x: ["bajo", "medio", "alto", "crítico"].index(x))

        prioridad_map = {
            "crítico": "Se requiere acción inmediata. Todos los indicadores de riesgo están elevados.",
            "alto": "Se recomienda intervención prioritaria. Varios factores de riesgo requieren atención.",
            "medio": "Monitoreo regular recomendado. Algunos indicadores requieren seguimiento.",
            "bajo": "Condiciones favorables. Mantener monitoreo de rutina.",
        }

        todas_recomendaciones = []
        for a in agentes:
            for r in a.get("recomendaciones", []):
                if r not in todas_recomendaciones:
                    todas_recomendaciones.append(r)

        return {
            "agente": self.name,
            "descripcion": self.description,
            "prioridad": prioridad,
            "resumen": prioridad_map.get(prioridad, ""),
            "recomendaciones_sintetizadas": todas_recomendaciones[:5],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────────────

def analyze(row: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta todos los agentes y retorna análisis completo."""
    agentes = [ClimateAgent(), ExposureAgent(), VulnerabilityAgent()]
    resultados = [a.analyze(row) for a in agentes]

    coordinador = CoordinatorAgent()
    sintesis = coordinador.analyze(row, resultados)

    return {
        "agentes": resultados,
        "coordinador": sintesis,
    }
