"""Smoke tests for Alerta pipeline."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb
import pandas as pd

DB = "data/alerta.duckdb"
errors = []

def check(desc, cond):
    if not cond:
        errors.append(f"FAIL: {desc}")
        print(f"  FAIL: {desc}")
    else:
        print(f"  OK: {desc}")

def main():
    print("Smoke tests for Alerta...\n")

    # 1. DB exists and has data
    assert os.path.exists(DB), f"DB not found: {DB}"
    con = duckdb.connect(DB)

    # 2. ira_resultados has rows, scores in [0,1]
    df = con.execute("SELECT ira_score FROM ira_resultados LIMIT 1").df()
    check("IRA table has data", not df.empty)
    if not df.empty:
        check("IRA score in [0,1]", 0 <= df["ira_score"].iloc[0] <= 1)

    # 3. ranking endpoint would work: data has municipios
    n = con.execute("SELECT COUNT(DISTINCT codigo_municipio) FROM ira_resultados").fetchone()[0]
    check("Distinct municipios > 0", n > 0)
    check("Distinct municipios >= 100", n >= 100)

    # 4. features table has all 26 variables
    cols = [r[0] for r in con.execute("SELECT column_name FROM information_schema.columns WHERE table_name='features_municipio_cultivo'").fetchall()]
    check("features_municipio_cultivo has >= 20 columns", len(cols) >= 20)
    check("nbi_total in features (SVE)", "nbi_total" in cols)
    check("tmax_media_7d in features (SPC)", "tmax_media_7d" in cols)

    # 5. Deforestation features exist
    n_def = con.execute("SELECT COUNT(*) FROM features_deforestacion").fetchone()[0]
    check("features_deforestacion has data", n_def > 0)

    # 6. NDVI features exist
    n_ndvi = con.execute("SELECT COUNT(*) FROM features_ndvi").fetchone()[0]
    check("features_ndvi has data", n_ndvi > 0)

    # 7. Features_clima has viento
    n_vi = con.execute("SELECT COUNT(*) FROM features_clima WHERE viento_media_30d IS NOT NULL").fetchone()[0]
    check("viento data in features_clima", n_vi > 0)

    # 8. NNet predictions exist
    n_nnet = con.execute("SELECT COUNT(*) FROM predicciones_nnet").fetchone()[0]
    check("predicciones_nnet has data", n_nnet > 0)

    con.close()

    print()
    if errors:
        print(f"{len(errors)} test(s) FAILED")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("All smoke tests PASSED")

if __name__ == "__main__":
    main()
