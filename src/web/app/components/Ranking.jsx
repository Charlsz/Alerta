"use client";
import { useState, useEffect, useCallback } from "react";
import RiskBadge from "./RiskBadge";
import FilterBar from "./FilterBar";

const PAGE_SIZE = 50;

function periodKey(value) {
  return String(value || "").slice(0, 10);
}

function rowKey(r) {
  return `${r.codigo_municipio}|${r.cultivo}|${periodKey(r.periodo)}`;
}

function selectedKey(selected) {
  if (!selected) return null;
  return `${selected.codigo}|${selected.cultivo}|${periodKey(selected.periodo)}`;
}

export default function Ranking({ onSelect, selected = null }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [order, setOrder] = useState("desc");
  const [cultivo, setCultivo] = useState("");
  const [departamento, setDepartamento] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchPage = useCallback(async (q, p, currentOrder, crop, dept) => {
    setLoading(true);
    const params = new URLSearchParams({
      limit: PAGE_SIZE,
      offset: (p - 1) * PAGE_SIZE,
      order: currentOrder,
    });
    if (q) params.set("search", q);
    if (crop) params.set("cultivo", crop);
    if (dept) params.set("departamento", dept);
    try {
      const res = await fetch(`/api/ranking?${params}`);
      const json = await res.json();
      setRows(json.data || []);
      setTotal(json.total || 0);
    } catch {
      setRows([]);
      setTotal(0);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchPage(debouncedSearch, page, order, cultivo, departamento);
  }, [debouncedSearch, page, order, cultivo, departamento, fetchPage]);

  const onFilterChange = (key, value) => {
    setPage(1);
    if (key === "cultivo") setCultivo(value);
    if (key === "departamento") setDepartamento(value);
  };

  const toggleOrder = () => {
    setPage(1);
    setOrder((current) => (current === "desc" ? "asc" : "desc"));
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const nextOrderLabel = order === "desc" ? "ascendente" : "descendente";
  const activeKey = selectedKey(selected);

  return (
    <div className="table-wrap">
      <div className="ranking-toolbar">
        <div>
          <h2 className="ranking-title">Ranking de riesgo</h2>
          <p className="ranking-subtitle">
            Cada fila es un municipio con un cultivo en su período más reciente.
            Haga clic para ver la misma información explicada en la ficha.
          </p>
        </div>
        <FilterBar cultivo={cultivo} departamento={departamento} onChange={onFilterChange} />
        <div className="search-bar">
          <div className="search-input-wrap">
            <input
              className="search-input"
              placeholder="Buscar municipio, departamento o cultivo…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              aria-label="Buscar en el ranking"
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => { setSearch(""); setPage(1); }}
                aria-label="Borrar búsqueda"
              >
                ✕
              </button>
            )}
          </div>
          <span className="search-count">{total.toLocaleString("es-CO")} resultados</span>
        </div>
      </div>

      {loading && !rows.length ? (
        <p className="empty-state">Cargando ranking...</p>
      ) : !rows.length ? (
        <p className="empty-state">
          No encontramos resultados con esos filtros.
          Pruebe quitar el cultivo, el departamento o la búsqueda.
        </p>
      ) : (
        <>
          <table className={`table${loading ? " table--loading" : ""}`}>
            <thead>
              <tr>
                <th>#</th>
                <th>Municipio</th>
                <th>Depto</th>
                <th>Cultivo</th>
                <th>
                  <button
                    className="sort-button"
                    type="button"
                    onClick={toggleOrder}
                    aria-label={`Ordenar IRA ${nextOrderLabel}`}
                    title={`Orden actual: ${order === "desc" ? "mayor a menor" : "menor a mayor"}`}
                  >
                    <span>IRA</span>
                    <span
                      className={`sort-arrow ${order === "desc" ? "sort-arrow--down" : "sort-arrow--up"}`}
                      aria-hidden="true"
                    >
                      {order === "desc" ? "↓" : "↑"}
                    </span>
                  </button>
                </th>
                <th>Nivel</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const key = rowKey(r);
                const isSelected = activeKey === key;
                return (
                  <tr
                    key={key}
                    className={isSelected ? "table-row--selected" : undefined}
                    aria-selected={isSelected}
                    onClick={() => onSelect?.({
                      codigo: r.codigo_municipio,
                      cultivo: r.cultivo,
                      periodo: r.periodo,
                    })}
                  >
                    <td>{start + i + 1}</td>
                    <td>{r.nombre_municipio || r.codigo_municipio}</td>
                    <td>{r.nombre_departamento || "—"}</td>
                    <td>{r.cultivo}</td>
                    <td>{r.ira_score != null ? r.ira_score.toFixed(3) : "—"}</td>
                    <td><RiskBadge nivel={r.ira_nivel} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
              .map((p, idx, arr) => (
                <span key={p} style={{ display: "contents" }}>
                  {idx > 0 && arr[idx - 1] !== p - 1 && <span className="page-info">…</span>}
                  <button className={p === page ? "page-active" : ""} onClick={() => setPage(p)}>{p}</button>
                </span>
              ))}
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Siguiente</button>
          </div>
        </>
      )}
    </div>
  );
}
