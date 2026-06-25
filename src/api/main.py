"""API REST para consultar resultados del IRA.

Endpoints:
    GET  /api/filters       — cultivos y departamentos disponibles
    GET  /api/ranking       — paginado, filtros por cultivo/departamento
    GET  /api/municipios    — GeoJSON con último IRA por municipio
    GET  /api/municipio/{codigo} — detalle por municipio y cultivo
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config

app = FastAPI(title="Alerta API", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _con():
    import duckdb
    con = duckdb.connect(config.duckdb_path)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def _table_exists(con, name):
    return bool(con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()[0])


@app.get("/api/filters")
def get_filters():
    con = _con()
    cultivos = []
    departamentos = []
    if _table_exists(con, "ira_resultados"):
        cultivos = [r[0] for r in con.execute("SELECT DISTINCT cultivo FROM ira_resultados ORDER BY cultivo").fetchall()]
    if _table_exists(con, "estaciones_municipio"):
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
    if not _table_exists(con, "ira_resultados"):
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
    if not _table_exists(con, "ira_resultados"):
        con.close()
        return {"type": "FeatureCollection", "features": []}

    rows = con.execute("""
        SELECT r.codigo_municipio, m.nombre_municipio, m.nombre_departamento,
               r.ira_score, r.ira_nivel, r.cultivo, r.periodo,
               ST_AsGeoJSON(m.geom) as geom
        FROM (
            SELECT DISTINCT ON (codigo_municipio) codigo_municipio, ira_score, ira_nivel, cultivo, periodo
            FROM ira_resultados
            ORDER BY codigo_municipio, ira_score DESC
        ) r
        JOIN estaciones_municipio m ON r.codigo_municipio = m.codigo_municipio
    """).fetchall()

    con.close()

    features = []
    for r in rows:
        import json
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
    if not _table_exists(con, "ira_resultados"):
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
    columns = ["codigo_municipio","cultivo","periodo","spc","sep","sve","ira_score","ira_nivel",
               "anomaly_score","is_anomaly","rendimiento_predicho","rendimiento_ic_inf","rendimiento_ic_sup",
               "importancia_top3","nombre_municipio","nombre_departamento"]
    return {"data": [dict(zip(columns, r)) for r in rows]}
