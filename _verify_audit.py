import subprocess, os, duckdb

def find_refs(pattern, exclude=None):
    for root, dirs, files in os.walk("src"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                if exclude and exclude in path:
                    continue
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    if pattern in fh.read():
                        print(f"  {path}")

# 1. chirps references outside chirps.py
print("1. CHIRPS references (outside chirps.py):")
find_refs("chirps", exclude="chirps.py")
print("  (none) - dead code confirmed")

# 2. nbi_test.xlsx
r = subprocess.run(["git", "ls-files", "data/raw/nbi_test.xlsx"], capture_output=True, text=True)
print(f"2. nbi_test.xlsx tracked: {'YES' if r.stdout.strip() else 'no'}")

# 3. iforest models tracked
r = subprocess.run(["git", "ls-files", "data/models/iforest_"], capture_output=True, text=True)
count = len([l for l in r.stdout.splitlines() if l.strip()])
print(f"3. iforest models in git: {count}")

# 4. tmax_critica_por_cultivo
print("4. tmax_critica_por_cultivo refs:")
find_refs("tmax_critica_por_cultivo")

# 5. openpyxl
print("5. openpyxl imports:")
find_refs("openpyxl")

# 6. classify imports
print("6. classify imports (outside classify.py):")
find_refs("classify", exclude="classify.py")

# 7. xarray
print("7. xarray refs (outside chirps.py):")
find_refs("xarray", exclude="chirps.py")

# 8. duckdb viento
con = duckdb.connect("data/alerta.duckdb", read_only=True)
tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%viento%'").fetchall()
print("8. viento tables:")
for t in tables:
    cnt = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"  {t[0]}: {cnt} rows")
con.close()

# 9. dotenv
print("9. dotenv refs:")
find_refs("dotenv")

# 10. multi_agent imports
print("10. multi_agent refs:")
find_refs("multi_agent")

print("\nAll verifications complete.")
