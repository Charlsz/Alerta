"use client";
import { useState, useEffect, useCallback } from "react";
import RiskBadge from "./RiskBadge";

const PAGE_SIZE = 50;

export default function Ranking({ onSelect }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const fetchPage = useCallback(async (q, p) => {
    setLoading(true);
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset: (p - 1) * PAGE_SIZE });
    if (q) params.set("search", q);
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

  useEffect(() => { fetchPage(search, page); }, [search, page, fetchPage]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;

  if (loading && !rows.length) return <p className="empty-state">Cargando ranking...</p>;
  if (!rows.length) return <p className="empty-state">Sin datos.</p>;

  return (
    <div className="table-wrap">
      <div className="search-bar">
        <input
          className="search-input"
          placeholder="Buscar municipio, departamento o cultivo…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <span className="search-count">{total} resultados</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Municipio</th><th>Depto</th><th>Cultivo</th><th>IRA</th><th>Nivel</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={`${r.codigo_municipio}-${r.cultivo}-${r.periodo}`}
              onClick={() => onSelect?.({ codigo: r.codigo_municipio, cultivo: r.cultivo, periodo: r.periodo })}
            >
              <td>{start + i + 1}</td>
              <td>{r.nombre_municipio || r.codigo_municipio}</td>
              <td>{r.nombre_departamento || "—"}</td>
              <td>{r.cultivo}</td>
              <td>{r.ira_score?.toFixed(3)}</td>
              <td><RiskBadge nivel={r.ira_nivel} /></td>
            </tr>
          ))}
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
    </div>
  );
}
