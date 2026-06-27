"use client";
import { useState, useMemo } from "react";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

const PAGE_SIZE = 50;

export default function Ranking({ onSelect }) {
  const { data, loading } = useAPI("/api/municipios");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const allRows = useMemo(() => {
    if (!data?.features) return [];
    let list = data.features.map((f) => ({
      codigo_municipio: f.properties.codigo_municipio,
      nombre_municipio: f.properties.municipio,
      nombre_departamento: f.properties.departamento,
      cultivo: f.properties.cultivo,
      ira_score: f.properties.ira_score,
      ira_nivel: f.properties.ira_nivel,
    }));
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((r) =>
        [r.nombre_municipio, r.nombre_departamento, r.cultivo, r.ira_nivel,
         String(r.ira_score ?? "")]
          .some((v) => v?.toLowerCase().includes(q))
      );
    }
    list.sort((a, b) => (b.ira_score ?? 0) - (a.ira_score ?? 0));
    return list;
  }, [data, search]);

  const totalPages = Math.max(1, Math.ceil(allRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRows = allRows.slice(start, start + PAGE_SIZE);

  if (loading) return <p className="empty-state">Cargando ranking...</p>;
  if (!allRows.length) return <p className="empty-state">Sin datos.</p>;

  return (
    <div className="table-wrap">
      <div className="search-bar">
        <input
          className="search-input"
          placeholder="Buscar municipio, departamento o cultivo…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <span className="search-count">{allRows.length} resultados</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Municipio</th><th>Depto</th><th>Cultivo</th><th>IRA</th><th>Nivel</th>
          </tr>
        </thead>
        <tbody>
          {pageRows.map((r, i) => (
            <tr
              key={r.codigo_municipio}
              onClick={() => onSelect?.({ codigo: r.codigo_municipio, cultivo: r.cultivo })}
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
        <button disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>Anterior</button>
        {Array.from({ length: totalPages }, (_, i) => i + 1)
          .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2)
          .map((p, idx, arr) => (
            <span key={p} style={{ display: "contents" }}>
              {idx > 0 && arr[idx - 1] !== p - 1 && <span className="page-info">…</span>}
              <button className={p === currentPage ? "page-active" : ""} onClick={() => setPage(p)}>{p}</button>
            </span>
          ))}
        <button disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>Siguiente</button>
      </div>
    </div>
  );
}
