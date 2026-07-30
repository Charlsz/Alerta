const LEVELS = { bajo: "bajo", medio: "medio", alto: "alto", critico: "critico" };

function normalizeLevel(nivel) {
  const value = String(nivel || "").trim();
  if (!value) return { label: "—", key: "" };

  const key = value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  if (key === "sin dato") return { label: "Sin dato", key: "" };

  const labelMap = {
    bajo: "Bajo",
    medio: "Medio",
    alto: "Alto",
    critico: "Crítico",
  };

  return { label: labelMap[key] || value, key };
}

export default function RiskBadge({ nivel }) {
  const normalized = normalizeLevel(nivel);
  const cls = `badge${LEVELS[normalized.key] ? ` badge--${LEVELS[normalized.key]}` : ""}`;
  return <span className={cls}>{normalized.label}</span>;
}
