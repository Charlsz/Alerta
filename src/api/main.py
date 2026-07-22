"""API REST para consultar resultados del IRA.

Endpoints:
    GET  /api/filters       — cultivos y departamentos disponibles
    GET  /api/ranking       — paginado, filtros por cultivo/departamento
    GET  /api/municipios    — GeoJSON con último IRA por municipio
    GET  /api/municipio/{codigo} — detalle por municipio y cultivo
    POST /api/municipio/{codigo}/chat — chatbot con LLM sobre el municipio
    GET  /api/municipio/{codigo}/multiagent — análisis multi-agente
    GET  /api/municipio/{codigo}/ndvi — serie temporal NDVI desde satélite
    GET  /api/municipio/{codigo}/deforestacion — datos de deforestación
"""
from __future__ import annotations
from src.ingestion.load_duckdb import get_connection, table_exists

import json
import os
from pathlib import Path

from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests

from config import config

from dotenv import load_dotenv
load_dotenv()

_IRA_COLUMNS = [
    "codigo_municipio","cultivo","periodo","spc","sep","sve","ira_score","ira_nivel",
    "anomaly_score","is_anomaly","rendimiento_predicho","rendimiento_ic_inf","rendimiento_ic_sup",
    "importancia_top3","rendimiento_nnet","nnet_ic_inf","nnet_ic_sup",
    "nombre_municipio","nombre_departamento",
]

app = FastAPI(title="Alerta API", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _con():
    import duckdb
    con = duckdb.connect(config.duckdb_path)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con



@app.get("/api/status")
def get_status():
    db_path = Path(config.duckdb_path)
    return {
        "db_exists": db_path.exists(),
        "last_updated": datetime.fromtimestamp(db_path.stat().st_mtime).isoformat() if db_path.exists() else None,
        "scheduler": "GitHub Actions diario (cron: 0 5,17 * * *)",
    }


@app.get("/api/filters")
def get_filters():
    con = _con()
    cultivos = []
    departamentos = []
    if table_exists(con, "ira_resultados"):
        cultivos = [r[0] for r in con.execute("SELECT DISTINCT cultivo FROM ira_resultados ORDER BY cultivo").fetchall()]
    if table_exists(con, "estaciones_municipio"):
        departamentos = [r[0] for r in con.execute("SELECT DISTINCT nombre_departamento FROM estaciones_municipio ORDER BY nombre_departamento").fetchall()]
    con.close()
    return {"cultivos": cultivos, "departamentos": departamentos}


@app.get("/api/ranking")
def get_ranking(
    cultivo: str = None,
    departamento: str = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"data": [], "total": 0}

    where = ["1=1"]
    if cultivo:
        where.append("r.cultivo = ?")
    if departamento:
        where.append("m.nombre_departamento = ?")
    clause = " AND ".join(where)

    params = [p for p in [cultivo, departamento] if p]

    total = con.execute(f"SELECT COUNT(*) FROM ira_resultados r LEFT JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio WHERE {clause}", params).fetchone()[0]
    rows = con.execute(f"""
        SELECT r.codigo_municipio, r.cultivo, r.periodo, r.ira_score, r.ira_nivel,
               r.anomaly_score, r.rendimiento_predicho,
               m.nombre_municipio, m.nombre_departamento
        FROM ira_resultados r
        LEFT JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio
        WHERE {clause}
        ORDER BY r.ira_score DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    con.close()
    return {
        "data": [dict(zip(["codigo_municipio","cultivo","periodo","ira_score","ira_nivel","anomaly_score","rendimiento_predicho","nombre_municipio","nombre_departamento"], r)) for r in rows],
        "total": total,
    }


@app.get("/api/municipios")
def get_municipios():
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"type": "FeatureCollection", "features": []}

    rows = con.execute("""
        SELECT r.codigo_municipio, m.nombre_municipio, m.nombre_departamento,
               r.ira_score, r.ira_nivel, r.cultivo, r.periodo,
               m.geom as geom
        FROM (
            SELECT DISTINCT ON (codigo_municipio) codigo_municipio, ira_score, ira_nivel, cultivo, periodo
            FROM ira_resultados
            ORDER BY codigo_municipio, ira_score DESC
        ) r
        JOIN municipios_geom m ON r.codigo_municipio = m.codigo_municipio
    """).fetchall()

    con.close()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(r[7]),
            "properties": {
                "codigo_municipio": r[0], "municipio": r[1], "departamento": r[2],
                "ira_score": r[3], "ira_nivel": r[4], "cultivo": r[5], "periodo": str(r[6]),
            },
        })
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/municipio/{codigo}")
def get_municipio(codigo: str, cultivo: str = None):
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"error": "no data"}

    where = ["r.codigo_municipio = ?"]
    if cultivo:
        where.append("r.cultivo = ?")
    clause = " AND ".join(where)
    params = [codigo] + ([cultivo] if cultivo else [])

    rows = con.execute(f"""
        SELECT r.*, m.nombre_municipio, m.nombre_departamento
        FROM ira_resultados r
        LEFT JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio
        WHERE {clause}
        ORDER BY r.periodo DESC
    """, params).fetchall()

    con.close()
    return {"data": [dict(zip(_IRA_COLUMNS, r)) for r in rows]}


@app.post("/api/municipio/{codigo}/chat")
def chat_municipio(codigo: str, body: dict = None):
    if body is None:
        body = {}
    question = (body.get("question") or "").strip()
    if not question:
        return {"answer": "Escribe una pregunta sobre el municipio."}

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return JSONResponse({"answer": "El asistente no está configurado (falta OPENROUTER_API_KEY)."}, status_code=503)

    # fetch municipio data
    con = _con()
    rows = con.execute(f"""
        SELECT r.*, m.nombre_municipio, m.nombre_departamento
        FROM ira_resultados r
        LEFT JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio
        WHERE r.codigo_municipio = ?
        ORDER BY r.periodo DESC
        LIMIT 30
    """, [codigo]).fetchall()
    con.close()

    if not rows:
        return {"answer": "No hay datos disponibles para este municipio."}

    data = [dict(zip(_IRA_COLUMNS, r)) for r in rows]

    system_prompt = """Eres un asistente experto en riesgo climático agrícola para Colombia, integrado en la plataforma "Alerta". Tu función es explicar los indicadores de riesgo agrícola a funcionarios públicos y agricultores en lenguaje claro y sencillo. Sin formato markdown, sin viñetas, sin guiones, sin asteriscos. Solo texto plano con puntos y comas.

INDICADORES:
- IRA (Índice de Riesgo Agrícola): 0-1, compuesto por SPC (peligro climático, peso 50%), SEP (exposición productiva, peso 30%), SVE (vulnerabilidad económica, peso 20%).
- Niveles: Bajo (<0.25), Medio (0.25-0.50), Alto (0.50-0.75), Crítico (>0.75).
- Anomalía (0-1): qué tan atípico es el municipio respecto a su historial (IsolationForest).
- Rendimiento predicho (t/ha): estimación del próximo rendimiento del cultivo con intervalo de confianza del 95%.
- Importancia top 3: variables que más influyen en el rendimiento predicho.

Usa los datos del municipio para responder. Sé conciso (máximo 3 párrafos). Si no sabes algo, dilo honestamente."""

    # ponytail: single prompt call, no streaming for now.
    # Add streaming when latency becomes an issue.
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Datos del municipio:\n{json.dumps(data, ensure_ascii=False, default=str)}\n\nPregunta: {question}"},
                ],
                "temperature": 0.3,
                "max_tokens": 600,
            },
            timeout=30,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"]
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Error al contactar el modelo: {str(e)[:200]}"}


@app.get("/api/municipio/{codigo}/multiagent")
def multiagent_municipio(codigo: str):
    """Análisis multi-agente del municipio."""
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"error": "no data"}

    rows = con.execute("""
        SELECT r.*, m.nombre_municipio, m.nombre_departamento
        FROM ira_resultados r
        LEFT JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio
        WHERE r.codigo_municipio = ?
        ORDER BY r.periodo DESC
        LIMIT 30
    """, [codigo]).fetchall()
    con.close()

    if not rows:
        return {"error": "no data"}

    row = dict(zip(_IRA_COLUMNS, rows[0]))

    from src.risk.multi_agent import analyze
    result = analyze(row)
    result["municipio"] = row.get("nombre_municipio")
    result["departamento"] = row.get("nombre_departamento")
    return result


@app.get("/api/municipio/{codigo}/ndvi")
def get_municipio_ndvi(codigo: str):
    """Serie temporal NDVI del municipio desde datos satelitales (MODIS)."""
    con = _con()
    if not table_exists(con, "features_ndvi"):
        con.close()
        return {"error": "no ndvi data"}

    rows = con.execute("""
        SELECT periodo, ndvi_media_30d, ndvi_anomalia_30d
        FROM features_ndvi
        WHERE codigo_municipio = ?
        ORDER BY periodo DESC
    """, [codigo]).fetchall()

    con.close()
    return {
        "data": [
            {"periodo": str(r[0]), "ndvi": r[1], "anomalia": r[2]}
            for r in rows
        ]
    }


@app.get("/api/municipio/{codigo}/deforestacion")
def get_municipio_deforestacion(codigo: str):
    """Datos de deforestación del municipio (GFW/Hansen, 2001-2025)."""
    con = _con()
    if not table_exists(con, "features_deforestacion"):
        con.close()
        return {"error": "no deforestation data"}

    rows = con.execute("""
        SELECT *
        FROM features_deforestacion
        WHERE codigo_municipio = ?
    """, [codigo]).fetchall()

    con.close()
    if not rows:
        return {"error": "no data for this municipio"}

    columns = ["codigo_municipio","deforestacion_2025","deforestacion_total_5y","deforestacion_total_10y",
               "primary_loss_5y","deforestacion_ha_promedio","n_anos_datos",
               "deforestacion_tendencia","deforestacion_tendencia_label"]
    return {"data": dict(zip(columns, rows[0]))}
