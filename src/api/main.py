"""API REST para consultar resultados del IRA.

Endpoints:
    GET  /api/filters       — cultivos y departamentos disponibles
    GET  /api/ranking       — paginado, filtros por cultivo/departamento
    GET  /api/municipios    — GeoJSON con último IRA por municipio
    GET  /api/municipio/{codigo} — detalle por municipio y cultivo
    POST /api/municipio/{codigo}/chat — chatbot con LLM sobre el municipio
    GET  /api/municipio/{codigo}/multiagent — análisis multi-agente

`chat` y `multiagent` reciben el alcance de la vista abierta en el frontend
(`scope`: general | cultivo, más `cultivo` y `periodo`) y solo analizan esos datos.
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


def _fmt_periodo(value) -> str | None:
    """Normalize period timestamps to YYYY-MM-DD so map/ranking/card compare equal."""
    if value is None:
        return None
    return str(value)[:10]


_IRA_SELECT = """
    SELECT r.*, m.nombre_municipio, m.nombre_departamento
    FROM ira_resultados r
    LEFT JOIN (SELECT DISTINCT codigo_municipio, nombre_municipio, nombre_departamento FROM estaciones_municipio WHERE codigo_municipio IS NOT NULL) m ON r.codigo_municipio = m.codigo_municipio
"""


def _ira_rows(con, codigo: str, cultivo: str = None, periodo: str = None, limit: int = None):
    """Filas de ira_resultados de un municipio, de la más reciente a la más antigua.

    `periodo` se compara por prefijo de fecha (10 caracteres) para aceptar tanto
    '2023-01-01' como '2023-01-01T00:00:00', que es lo que puede enviar el frontend.
    """
    where = ["r.codigo_municipio = ?"]
    params = [codigo]
    if cultivo:
        where.append("r.cultivo = ?")
        params.append(cultivo)
    if periodo:
        where.append("CAST(r.periodo AS VARCHAR) LIKE ?")
        params.append(f"{str(periodo)[:10]}%")
    sql = f"{_IRA_SELECT} WHERE {' AND '.join(where)} ORDER BY r.periodo DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = [dict(zip(_IRA_COLUMNS, r)) for r in con.execute(sql, params).fetchall()]
    for row in rows:
        row["periodo"] = _fmt_periodo(row.get("periodo"))
    return rows


def _top3(row: dict):
    """importancia_top3 se guarda como JSON en texto; devolverlo ya parseado."""
    v = row.get("importancia_top3")
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return v


def _fila_resumen(row: dict) -> dict:
    """Los campos de una fila (cultivo × período) que la tarjeta muestra en pantalla."""
    return {
        "cultivo": row.get("cultivo"),
        "periodo": str(row.get("periodo"))[:10],
        "ira_score": row.get("ira_score"),
        "ira_nivel": row.get("ira_nivel"),
        "spc": row.get("spc"),
        "sep": row.get("sep"),
        "sve": row.get("sve"),
        "rendimiento_predicho": row.get("rendimiento_predicho"),
        "anomaly_score": row.get("anomaly_score"),
    }


def _ultima_por_cultivo(rows: list[dict]) -> list[dict]:
    """Última fila de cada cultivo, ordenada por IRA desc.

    Es la misma lista que la tarjeta usa para las pestañas de cultivo y para la vista General.
    """
    latest: dict[str, dict] = {}
    for r in rows:
        c = r.get("cultivo")
        if c not in latest or str(r.get("periodo")) > str(latest[c].get("periodo")):
            latest[c] = r
    return sorted(latest.values(), key=lambda r: r.get("ira_score") or 0, reverse=True)


def _periodo_por_defecto(rows: list[dict]) -> dict | None:
    """Fila que la tarjeta muestra por defecto: el período más reciente con rendimiento;
    si ninguno tiene rendimiento, simplemente el más reciente."""
    if not rows:
        return None
    con_datos = [r for r in rows if r.get("rendimiento_predicho") is not None]
    return max(con_datos or rows, key=lambda r: str(r.get("periodo")))


def _ndvi_serie(con, codigo: str) -> list[dict] | None:
    if not table_exists(con, "features_ndvi"):
        return None
    rows = con.execute("""
        SELECT periodo, ndvi_media_30d, ndvi_anomalia_30d
        FROM features_ndvi
        WHERE codigo_municipio = ?
        ORDER BY periodo DESC
    """, [codigo]).fetchall()
    return [{"periodo": str(r[0]), "ndvi": r[1], "anomalia": r[2]} for r in rows]


def _deforestacion_fila(con, codigo: str) -> dict | None:
    if not table_exists(con, "features_deforestacion"):
        return None
    columns = [r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='features_deforestacion' ORDER BY ordinal_position"
    ).fetchall()]
    rows = con.execute(f"""
        SELECT {', '.join(columns)}
        FROM features_deforestacion
        WHERE codigo_municipio = ?
    """, [codigo]).fetchall()
    return dict(zip(columns, rows[0])) if rows else None


def _deforestacion_resumen(d: dict | None) -> dict | None:
    """Solo las cuatro cifras de deforestación que se ven en la tarjeta."""
    if not d:
        return None
    ultimo = next(
        ((k, v) for k, v in d.items()
         if k.startswith("deforestacion_") and not any(x in k for x in ("total", "promedio", "tendencia"))),
        None,
    )
    return {
        "ultimo_anio_columna": ultimo[0] if ultimo else None,
        "ultimo_anio_ha": ultimo[1] if ultimo else None,
        "total_5_anios_ha": d.get("deforestacion_total_5y"),
        "total_10_anios_ha": d.get("deforestacion_total_10y"),
        "tendencia": d.get("deforestacion_tendencia_label"),
    }



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
    search: str = None,
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"data": [], "total": 0}

    where = ["r._rn = 1"]
    params = []
    if cultivo:
        where.append("r.cultivo = ?")
        params.append(cultivo)
    if departamento:
        where.append("m.nombre_departamento = ?")
        params.append(departamento)
    if search:
        where.append("(m.nombre_municipio ILIKE ? OR m.nombre_departamento ILIKE ? OR r.cultivo ILIKE ?)")
        q = f"%{search}%"
        params.extend([q, q, q])
    clause = " AND ".join(where)
    wheresql = f"""FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY codigo_municipio, cultivo ORDER BY periodo DESC) as _rn
        FROM ira_resultados
    ) r
    LEFT JOIN (SELECT DISTINCT codigo_municipio, nombre_municipio, nombre_departamento FROM estaciones_municipio WHERE codigo_municipio IS NOT NULL) m
        ON r.codigo_municipio = m.codigo_municipio
    WHERE {clause}"""

    # Whitelist only — never interpolate raw query strings into ORDER BY.
    order_dir = "ASC" if order.lower() == "asc" else "DESC"
    total = con.execute(f"SELECT COUNT(*) {wheresql}", params).fetchone()[0]
    rows = con.execute(f"""
        SELECT r.codigo_municipio, r.cultivo, r.periodo, r.ira_score, r.ira_nivel,
               r.anomaly_score, r.rendimiento_predicho,
               m.nombre_municipio, m.nombre_departamento
        {wheresql}
        ORDER BY r.ira_score {order_dir} NULLS LAST
        LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    con.close()
    keys = ["codigo_municipio","cultivo","periodo","ira_score","ira_nivel","anomaly_score","rendimiento_predicho","nombre_municipio","nombre_departamento"]
    data = []
    for r in rows:
        item = dict(zip(keys, r))
        item["periodo"] = _fmt_periodo(item.get("periodo"))
        data.append(item)
    return {"data": data, "total": total}


@app.get("/api/municipios")
def get_municipios():
    """Map colors use the highest IRA among each municipio's *latest* period per cultivo.

    This matches ranking row selection (latest period), so map tooltip and card open
    on the same (cultivo, periodo, ira_score) the table would show for that crop.
    """
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
            FROM (
                SELECT codigo_municipio, ira_score, ira_nivel, cultivo, periodo,
                       ROW_NUMBER() OVER (
                           PARTITION BY codigo_municipio, cultivo
                           ORDER BY periodo DESC
                       ) AS _rn
                FROM ira_resultados
            ) latest
            WHERE _rn = 1
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
                "ira_score": r[3], "ira_nivel": r[4], "cultivo": r[5],
                "periodo": _fmt_periodo(r[6]),
            },
        })
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/municipio/{codigo}")
def get_municipio(codigo: str, cultivo: str = None, periodo: str = None):
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"error": "no data"}
    rows = _ira_rows(con, codigo, cultivo=cultivo, periodo=periodo)
    con.close()
    return {"data": rows}


def _contexto_general(rows: list[dict]) -> dict:
    """Réplica de la vista General de la tarjeta: un cultivo por fila, con su último período."""
    ultimas = _ultima_por_cultivo(rows)
    scores = [r["ira_score"] for r in ultimas if r.get("ira_score") is not None]
    niveles: dict[str, int] = {}
    for r in ultimas:
        n = r.get("ira_nivel") or "Sin dato"
        niveles[n] = niveles.get(n, 0) + 1
    return {
        "vista": "general",
        "que_muestra": (
            "Resumen del municipio: todos los cultivos reportados, cada uno con su último "
            "período disponible. No hay un cultivo ni un período seleccionado."
        ),
        "total_cultivos": len(ultimas),
        "ira_promedio": round(sum(scores) / len(scores), 4) if scores else None,
        "distribucion_niveles": niveles,
        "mayor_riesgo": [_fila_resumen(r) for r in ultimas[:3]],
        "menor_riesgo": [_fila_resumen(r) for r in list(reversed(ultimas))[:3]],
        "cultivos": [_fila_resumen(r) for r in ultimas],
    }


def _contexto_cultivo(rows_cultivo: list[dict], periodo: str = None) -> dict | None:
    """Réplica de la vista de detalle: un solo cultivo en un solo período.

    `rows_cultivo` son todas las filas de ese cultivo (todos los períodos); el histórico
    va aparte y marcado como referencia para que el modelo no lo mezcle con el período elegido.
    """
    foco = None
    if periodo:
        pref = str(periodo)[:10]
        foco = next((r for r in rows_cultivo if str(r.get("periodo"))[:10] == pref), None)
    if foco is None:
        foco = _periodo_por_defecto(rows_cultivo)
    if foco is None:
        return None

    detalle = _fila_resumen(foco)
    detalle.update({
        "rendimiento_ic_inf": foco.get("rendimiento_ic_inf"),
        "rendimiento_ic_sup": foco.get("rendimiento_ic_sup"),
        "rendimiento_nnet": foco.get("rendimiento_nnet"),
        "is_anomaly": foco.get("is_anomaly"),
        "importancia_top3": _top3(foco),
    })
    return {
        "vista": "cultivo",
        "que_muestra": f"Detalle del cultivo {foco.get('cultivo')} en el período {detalle['periodo']}.",
        "cultivo": foco.get("cultivo"),
        "periodo_seleccionado": detalle["periodo"],
        "datos_del_periodo": detalle,
        "historial_del_cultivo": [_fila_resumen(r) for r in rows_cultivo[:24]],
    }


_CHAT_INDICADORES = """INDICADORES:
- IRA (Índice de Riesgo Agrícola): 0-1, compuesto por SPC (peligro climático, peso 50%), SEP (exposición productiva, peso 30%), SVE (vulnerabilidad económica, peso 20%).
- Niveles: Bajo (<0.25), Medio (0.25-0.50), Alto (0.50-0.75), Crítico (>0.75).
- Anomalía (0-1): qué tan atípico es el municipio respecto a su historial (IsolationForest).
- Rendimiento predicho (t/ha): estimación del próximo rendimiento del cultivo con intervalo de confianza del 95%.
- Importancia top 3: variables que más influyen en el rendimiento predicho."""


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

    cultivo = body.get("cultivo")
    periodo = body.get("periodo")
    # La vista que el usuario tiene abierta. Si no llega, se deduce del cultivo (compatibilidad).
    scope = str(body.get("scope") or ("cultivo" if cultivo else "general")).lower()
    if scope not in ("general", "cultivo"):
        scope = "cultivo" if cultivo else "general"
    if scope == "cultivo" and not cultivo:
        scope = "general"

    # El contexto se arma con los mismos datos que la tarjeta tiene en pantalla:
    # en General, un cultivo por fila con su último período; en detalle, solo ese cultivo y período.
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"answer": "Todavía no hay resultados del IRA cargados."}
    rows = _ira_rows(con, codigo, cultivo=cultivo if scope == "cultivo" else None)
    ndvi = _ndvi_serie(con, codigo)
    defor = _deforestacion_resumen(_deforestacion_fila(con, codigo))
    con.close()

    if not rows:
        if scope == "cultivo":
            return {"answer": f"No hay datos del cultivo {cultivo} en este municipio."}
        return {"answer": "No hay datos disponibles para este municipio."}

    if scope == "general":
        ctx = _contexto_general(rows)
        alcance = (
            "La vista actual es GENERAL: el resumen de todos los cultivos del municipio, cada uno "
            "con su último período disponible. Habla del municipio como conjunto, usando el IRA "
            "promedio, la distribución de niveles y los cultivos de mayor y menor riesgo. "
            "Si preguntan por un cultivo puntual, usa solo la fila de ese cultivo que está en el contexto."
        )
    else:
        ctx = _contexto_cultivo(rows, periodo)
        if ctx is None:
            return {"answer": f"No hay datos del cultivo {cultivo} en este municipio."}
        alcance = (
            f"La vista actual es el cultivo {ctx['cultivo']} en el período {ctx['periodo_seleccionado']}. "
            "Analiza únicamente ese cultivo y ese período: las cifras que debes usar son las de "
            "datos_del_periodo. No hables de otros cultivos del municipio. El historial de otros "
            "períodos está solo como referencia y se usa únicamente si preguntan por la evolución en el tiempo."
        )

    contexto = {
        "municipio": rows[0].get("nombre_municipio") or codigo,
        "departamento": rows[0].get("nombre_departamento"),
        **ctx,
    }
    if ndvi:
        contexto["ndvi_satelital"] = {"actual": ndvi[0], "serie_reciente": ndvi[:6]}
    if defor:
        contexto["deforestacion"] = defor

    system_prompt = f"""Eres un asistente experto en riesgo climático agrícola para Colombia. Habla en lenguaje claro y sencillo como para un agricultor. No uses formato markdown, ni viñetas, ni guiones, ni asteriscos. Solo texto plano con puntos y comas.

REGLA IMPORTANTE: No expliques tu razonamiento ni muestres tu proceso de análisis. Responde ÚNICAMENTE el texto final del análisis, sin prefacios, sin introducciones como "El usuario quiere...", sin "Basado en los datos...". Empieza directamente con la respuesta.

{_CHAT_INDICADORES}

ALCANCE DE LA RESPUESTA (obligatorio):
- {alcance}
- Usa exclusivamente las cifras del bloque CONTEXTO: es exactamente lo que el usuario está viendo en pantalla. No inventes ni estimes valores que no estén ahí.
- Si preguntan por un cultivo, un período o un municipio que no aparece en el CONTEXTO, dilo y sugiere seleccionarlo en la tarjeta.

Sé conciso (máximo 3 párrafos). Si no sabes algo, dilo honestamente."""

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
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"CONTEXTO (lo que el usuario está viendo en pantalla):\n{json.dumps(contexto, ensure_ascii=False, default=str)}\n\nPregunta: {question}\n\nIMPORTANTE: No expliques tu razonamiento ni describas los datos. Escribe UNICAMENTE la respuesta final, sin prefacios."},
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


def _fila_promedio(rows: list[dict]) -> dict:
    """Fila sintética con el promedio de los sub-índices — el equivalente al IRA promedio
    que muestra la vista General, para que los agentes analicen el municipio y no un cultivo al azar."""
    def prom(campo):
        vals = [r.get(campo) for r in rows if r.get(campo) is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "cultivo": "los cultivos del municipio",
        "periodo": max((str(r.get("periodo")) for r in rows), default="")[:10],
        "spc": prom("spc"),
        "sep": prom("sep"),
        "sve": prom("sve"),
        "ira_score": prom("ira_score"),
        "rendimiento_predicho": prom("rendimiento_predicho"),
        "nombre_municipio": rows[0].get("nombre_municipio"),
        "nombre_departamento": rows[0].get("nombre_departamento"),
    }


@app.get("/api/municipio/{codigo}/multiagent")
def multiagent_municipio(codigo: str, cultivo: str = None, periodo: str = None, scope: str = None):
    """Análisis multi-agente sobre lo que está en pantalla.

    scope=general → promedio de los últimos períodos de todos los cultivos;
    scope=cultivo → solo el cultivo y período seleccionados.
    """
    con = _con()
    if not table_exists(con, "ira_resultados"):
        con.close()
        return {"error": "no data"}

    scope = (scope or ("cultivo" if cultivo else "general")).lower()
    if scope != "general" and not cultivo:
        scope = "general"

    rows = _ira_rows(con, codigo, cultivo=cultivo if scope == "cultivo" else None)
    con.close()

    if not rows:
        return {"error": "no data"}

    if scope == "general":
        row = _fila_promedio(_ultima_por_cultivo(rows))
    else:
        row = None
        if periodo:
            pref = str(periodo)[:10]
            row = next((r for r in rows if str(r.get("periodo"))[:10] == pref), None)
        row = row or _periodo_por_defecto(rows)

    from src.risk.multi_agent import analyze
    result = analyze(row)
    result["alcance"] = scope
    result["cultivo"] = row.get("cultivo")
    result["periodo"] = str(row.get("periodo"))[:10]
    result["municipio"] = row.get("nombre_municipio")
    result["departamento"] = row.get("nombre_departamento")
    return result


@app.get("/api/municipio/{codigo}/ndvi")
def get_municipio_ndvi(codigo: str):
    """Serie temporal NDVI del municipio desde datos satelitales (MODIS)."""
    con = _con()
    serie = _ndvi_serie(con, codigo)
    con.close()
    if serie is None:
        return {"error": "no ndvi data"}
    return {"data": serie}


@app.get("/api/municipio/{codigo}/deforestacion")
def get_municipio_deforestacion(codigo: str):
    """Datos de deforestación del municipio (GFW/Hansen, 2001-2025)."""
    con = _con()
    if not table_exists(con, "features_deforestacion"):
        con.close()
        return {"error": "no deforestation data"}
    fila = _deforestacion_fila(con, codigo)
    con.close()
    if not fila:
        return {"error": "no data for this municipio"}
    return {"data": fila}
