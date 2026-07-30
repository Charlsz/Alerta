"use client";
import useAPI from "../hooks/useAPI";

export default function FilterBar({ cultivo, departamento, onChange }) {
  const { data } = useAPI("/api/filters");

  return (
    <div className="filters" role="group" aria-label="Filtros del ranking">
      <label className="filter-field">
        <span className="filter-label">Cultivo</span>
        <select
          className="filter-select"
          value={cultivo || ""}
          onChange={(e) => onChange("cultivo", e.target.value)}
        >
          <option value="">Todos los cultivos</option>
          {(data?.cultivos || []).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </label>
      <label className="filter-field">
        <span className="filter-label">Departamento</span>
        <select
          className="filter-select"
          value={departamento || ""}
          onChange={(e) => onChange("departamento", e.target.value)}
        >
          <option value="">Todos los departamentos</option>
          {(data?.departamentos || []).map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </label>
      {(cultivo || departamento) && (
        <button
          type="button"
          className="filter-clear"
          onClick={() => {
            onChange("cultivo", "");
            onChange("departamento", "");
          }}
        >
          Quitar filtros
        </button>
      )}
    </div>
  );
}
